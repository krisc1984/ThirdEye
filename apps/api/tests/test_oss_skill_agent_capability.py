from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.project import Project, normalize_slug
from app.services.storage import JsonStorage


TARGET_PROJECT_PATH = Path(r"D:\python_project\code-review")


def _seed_playbook(client: TestClient) -> str:
    project_root = Path(__file__).parent / "fixtures" / "sample_project"
    project = client.post(
        "/projects",
        json={"root_path": str(project_root), "extra_ignore_patterns": [], "name": "Sample Project"},
    ).json()
    metadata = client.post("/playbooks/distill", json={"project_id": project["id"]}).json()
    return metadata["id"]


def _seed_default_provider(client: TestClient) -> None:
    client.post(
        "/model-providers",
        json={
            "id": "xunfei",
            "name": "Default Provider",
            "provider_type": "openai",
            "model": "provider/default-model",
            "api_shape": "responses",
            "api_key": "secret",
        },
    )


def _save_external_project() -> str:
    project = Project(
        id="proj_external_code_review",
        name="code-review",
        root_path=TARGET_PROJECT_PATH,
        slug=normalize_slug("code-review"),
        languages=["Python"],
        frameworks=[],
        created_at=datetime.utcnow(),
    )
    storage = JsonStorage(settings.data_dir)
    payload = project.model_dump(mode="json")
    payload["latest_scan"] = {
        "root_path": str(TARGET_PROJECT_PATH),
        "total_files": 0,
        "scanned_files": 0,
        "skipped_files": 0,
        "languages": {"Python": 0},
        "docs": [],
        "tests": [],
        "config_files": [],
        "entrypoint_candidates": [],
        "sensitive_warnings": [],
    }
    storage.save_json("projects", project.id, payload)
    return project.id


def test_review_session_exposes_oss_skill_for_complex_external_project_request(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)
    project_id = _save_external_project()

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": project_id,
            "mode": "standard",
            "model_provider_id": "xunfei",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    monkeypatch.setattr(
        "app.agents.sdk_chat._maybe_run_oss_skill_preflight",
        lambda query: (
            "已通过后端 deterministic preflight 处理 oss-skill 本地项目蒸馏请求，"
            "避免模型自行发起脆弱的 bash/write_file_chunk 工具调用。"
        )
        if "oss-skill" in query and str(TARGET_PROJECT_PATH) in query
        else None,
    )

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={
            "message": (
                '请调用 oss-skill 蒸馏 "D:\\python_project\\code-review" 项目，'
                "并验证 agent 调用复杂 skill 的可用性。"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["resolved_provider_id"] is None
    assert "deterministic preflight" in body["latest_summary"]
