from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.sdk_runtime import TextAgentRunResult
from app.main import app
from app.services.review_session_event_log import ReviewSessionEventLog


def _seed_playbook(client: TestClient) -> str:
    project_root = Path(__file__).parent / "fixtures" / "sample_project"
    project = client.post(
        "/projects",
        json={"root_path": str(project_root), "extra_ignore_patterns": [], "name": "Sample Project"},
    ).json()
    metadata = client.post("/playbooks/distill", json={"project_id": project["id"]}).json()
    return metadata["id"]


def test_review_session_lifecycle_events_are_logged(monkeypatch, tmp_path) -> None:
    from app.core.config import settings

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

        async def fake_run_text_agent(**kwargs):
            return TextAgentRunResult(output_text="这是一次完成的回复")

        monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)

        message_response = client.post(
            f"/reviews/sessions/{session_id}/messages",
            json={"message": "请评审一下这个方案"},
        )
        assert message_response.status_code == 200

        event_log = ReviewSessionEventLog(tmp_path / "review-session-events")
        events = event_log.list_events(session_id)
        event_types = [event.event_type for event in events]

        assert "session_started" in event_types
        assert "user_message" in event_types
        assert "assistant_message" in event_types
        assert "session_status_changed" in event_types
        assert "session_completed" in event_types
    finally:
        settings.data_dir = original_data_dir


def test_review_session_completion_records_evaluation_event(monkeypatch, tmp_path) -> None:
    from app.core.config import settings

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

        async def fake_run_text_agent(**kwargs):
            return TextAgentRunResult(output_text="最终回复")

        monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)

        message_response = client.post(
            f"/reviews/sessions/{session_id}/messages",
            json={"message": "请评审一下这个方案"},
        )
        assert message_response.status_code == 200

        event_log = ReviewSessionEventLog(tmp_path / "review-session-events")
        event_types = [event.event_type for event in event_log.list_events(session_id)]

        assert "evaluation_recorded" in event_types
    finally:
        settings.data_dir = original_data_dir


def test_review_session_completion_records_anomaly_event_for_repeated_tool_failure(monkeypatch, tmp_path) -> None:
    from app.core.config import settings

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

        event_log = ReviewSessionEventLog(tmp_path / "review-session-events")
        anomaly_events = [event for event in event_log.list_events(session_id) if event.event_type == "anomaly_detected"]

        assert anomaly_events
        assert anomaly_events[0].payload["code"] == "repeated_tool_failure"
    finally:
        settings.data_dir = original_data_dir
