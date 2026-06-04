from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _seed_playbook(client: TestClient) -> str:
    project_root = Path(__file__).parent / "fixtures" / "sample_project"
    project = client.post(
        "/projects",
        json={"root_path": str(project_root), "extra_ignore_patterns": [], "name": "Sample Project"},
    ).json()
    metadata = client.post("/playbooks/distill", json={"project_id": project["id"]}).json()
    return metadata["id"]


def test_observability_sessions_list_only_shows_sessions_with_event_logs(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        list_response = client.get("/observability/sessions")
        assert list_response.status_code == 200
        body = list_response.json()
        assert any(item["session_id"] == session_id for item in body)
    finally:
        settings.data_dir = original_data_dir


def test_observability_sessions_list_includes_evaluation_and_anomaly_summary(monkeypatch, tmp_path) -> None:
    from app.core.config import settings
    from app.agents.sdk_runtime import TextAgentRunResult

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)
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

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        async def fake_run_text_agent(
            *,
            runtime_event_callback=None,
            **kwargs,
        ):
            assert runtime_event_callback is not None
            for index in range(3):
                runtime_event_callback(
                    {
                        "kind": "tool",
                        "phase": "end",
                        "runtime_id": f"tool_call_{index}",
                        "tool_call_id": f"tool_call_{index}",
                        "tool_name": "read_file",
                        "turn": 1,
                        "result": "Error: missing file",
                        "ok": False,
                    }
                )
            return TextAgentRunResult(output_text="最终回复")

        monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)
        message_response = client.post(
            f"/reviews/sessions/{session_id}/messages",
            json={"message": "请评审一下这个方案"},
        )
        assert message_response.status_code == 200

        list_response = client.get("/observability/sessions")
        assert list_response.status_code == 200
        target = next(item for item in list_response.json() if item["session_id"] == session_id)

        assert target["anomaly_count"] >= 1
        assert target["evaluation_grade"] == "failed"
    finally:
        settings.data_dir = original_data_dir


def test_observability_timeline_returns_event_entries(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        response = client.get(f"/observability/sessions/{session_id}/timeline")
        assert response.status_code == 200
        body = response.json()
        assert body
        assert body[0]["event_type"] == "session_started"
        assert "title" in body[0]
        assert "summary" in body[0]
    finally:
        settings.data_dir = original_data_dir


def test_observability_tasks_returns_built_task_tree(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        response = client.get(f"/observability/sessions/{session_id}/tasks")
        assert response.status_code == 200
        body = response.json()
        assert body
        assert body[0]["kind"] == "session"
    finally:
        settings.data_dir = original_data_dir


def test_observability_metrics_returns_aggregated_counts(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        response = client.get(f"/observability/sessions/{session_id}/metrics")
        assert response.status_code == 200
        body = response.json()
        assert body["llm_turn_count"] == 0
        assert body["tool_call_count"] == 0
        assert body["tool_error_count"] == 0
    finally:
        settings.data_dir = original_data_dir


def test_observability_session_detail_returns_summary(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        response = client.get(f"/observability/sessions/{session_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == session_id
        assert body["playbook_id"] == playbook_id
    finally:
        settings.data_dir = original_data_dir


def test_observability_events_returns_raw_event_stream(tmp_path) -> None:
    from app.core.config import settings

    original_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    try:
        client = TestClient(app)
        playbook_id = _seed_playbook(client)

        session_response = client.post(
            "/reviews/sessions",
            json={"playbook_id": playbook_id, "mode": "standard"},
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        response = client.get(f"/observability/sessions/{session_id}/events")
        assert response.status_code == 200
        body = response.json()
        assert body
        assert body[0]["event_type"] == "session_started"
    finally:
        settings.data_dir = original_data_dir
