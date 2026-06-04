from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.sdk_runtime import AgentResumeError, TextAgentRunResult
from app.main import app


def _seed_playbook_and_session(client: TestClient) -> tuple[str, str]:
    project = client.post(
        "/projects",
        json={
            "root_path": str((__import__("pathlib").Path(__file__).parent / "fixtures" / "sample_project").resolve()),
            "extra_ignore_patterns": [],
            "name": "Sample Project",
        },
    ).json()
    playbook = client.post("/playbooks/distill", json={"project_id": project["id"]}).json()
    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook["id"], "project_id": project["id"], "mode": "standard"},
    ).json()
    return playbook["id"], session["id"]


def test_review_report_assistant_returns_generated_markdown():
    client = TestClient(app)
    playbook_id, session_id = _seed_playbook_and_session(client)

    client.post(
        "/model-providers",
        json={
            "id": "report-writer",
            "name": "Report Writer",
            "provider_type": "openai",
            "model": "gpt-5.4",
        },
    )

    session_payload = client.get(f"/reviews/sessions/{session_id}").json()
    session_payload["resolved_provider_id"] = "report-writer"
    (__import__("pathlib").Path(__import__("app.core.config", fromlist=["settings"]).settings.data_dir) / "review-sessions" / f"{session_id}.json").write_text(
        __import__("json").dumps(session_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    async def fake_run_text_agent(*, name, instructions, user_input, provider_config, session=None, tools=None, model_settings=None):
        assert name == "ThirdEye Review Report Writer"
        assert "当前 Markdown 草稿" in user_input
        return TextAgentRunResult(
            output_text="## 编辑说明\n已重写。\n\n## Markdown 成稿\n# 正式报告\n\n- 已生成"
        )

    with patch("app.agents.report_writer.run_text_agent", fake_run_text_agent):
        response = client.post(
            "/reviews/report-assistant",
            json={
                "session_id": session_id,
                "playbook_id": playbook_id,
                "markdown": "# 草稿",
                "instruction": "重写为正式报告",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "llm"
    assert "# 正式报告" in body["suggested_markdown"]
    assert "已重写" in body["reply"]


def test_review_report_assistant_timeout_falls_back_to_existing_markdown():
    client = TestClient(app)
    playbook_id, session_id = _seed_playbook_and_session(client)

    client.post(
        "/model-providers",
        json={
            "id": "report-writer",
            "name": "Report Writer",
            "provider_type": "openai",
            "model": "gpt-5.4",
        },
    )

    session_payload = client.get(f"/reviews/sessions/{session_id}").json()
    session_payload["resolved_provider_id"] = "report-writer"
    (__import__("pathlib").Path(__import__("app.core.config", fromlist=["settings"]).settings.data_dir) / "review-sessions" / f"{session_id}.json").write_text(
        __import__("json").dumps(session_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    async def fake_run_text_agent(*, name, instructions, user_input, provider_config, session=None, tools=None, model_settings=None):
        raise AgentResumeError("Request timed out.", resume_state_json=None, resumable=False)

    with patch("app.agents.report_writer.run_text_agent", fake_run_text_agent):
        response = client.post(
            "/reviews/report-assistant",
            json={
                "session_id": session_id,
                "playbook_id": playbook_id,
                "markdown": "# 草稿",
                "instruction": "重写为正式报告",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["resolved_provider_id"] is None
    assert body["suggested_markdown"] == "# 草稿"
    assert "失败原因" in body["reply"]
    assert "Request timed out." in body["execution_note"]
