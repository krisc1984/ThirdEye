from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import app


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def _create_project(client: TestClient) -> str:
    response = client.post(
        "/projects",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": [], "name": "Sample Project"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_distill_and_get_playbook():
    client = TestClient(app)
    project_id = _create_project(client)

    distill = client.post("/playbooks/distill", json={"project_id": project_id})

    assert distill.status_code == 200
    metadata = distill.json()
    assert metadata["project_id"] == project_id
    assert metadata["status"] == "active"

    detail = client.get(f"/playbooks/{metadata['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert "## Activation Rules" in body["skill_markdown"]
    assert len(body["rules"]) >= 5
    assert body["evidence"]


def test_list_playbooks():
    client = TestClient(app)
    project_id = _create_project(client)
    metadata = client.post("/playbooks/distill", json={"project_id": project_id}).json()

    response = client.get("/playbooks")

    assert response.status_code == 200
    assert any(item["id"] == metadata["id"] for item in response.json())


def test_get_artifact():
    client = TestClient(app)
    project_id = _create_project(client)
    metadata = client.post("/playbooks/distill", json={"project_id": project_id}).json()

    response = client.get(f"/playbooks/{metadata['id']}/artifact/playbook.skill.md")

    assert response.status_code == 200
    assert response.json()["name"] == "playbook.skill.md"
    assert "Review Playbook" in response.json()["content"]


def test_distill_rejects_missing_project():
    client = TestClient(app)

    response = client.post("/playbooks/distill", json={"project_id": "proj_missing"})

    assert response.status_code == 404


def test_distill_falls_back_when_provider_call_fails(monkeypatch):
    client = TestClient(app)
    project_id = _create_project(client)
    client.post(
        "/model-providers",
        json={
            "id": "router-api",
            "name": "Router",
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "secret",
        },
    )

    async def broken_distill(*_args, **_kwargs):
        raise RuntimeError("Example Domain")

    monkeypatch.setattr("app.api.playbooks.run_playbook_distillation", broken_distill)

    response = client.post(
        "/playbooks/distill",
        json={"project_id": project_id, "model_provider_id": "router-api"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert "fell back" in body["execution_note"]
