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


def test_review_session_runtime_events_are_logged(monkeypatch, tmp_path) -> None:
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
            name,
            instructions,
            user_input,
            provider_config,
            session=None,
            tools=None,
            model_settings=None,
            resume_state=None,
            runtime_event_callback=None,
        ):
            callback = runtime_event_callback
            assert callback is not None
            callback(
                {
                    "kind": "llm",
                    "phase": "start",
                    "runtime_id": "llm_turn_1",
                    "provider_id": "xunfei",
                    "model": "provider/default-model",
                    "turn": 1,
                    "tool_arguments": '{"system_prompt":"x"}',
                }
            )
            callback(
                {
                    "kind": "tool",
                    "phase": "start",
                    "runtime_id": "tool_call_1",
                    "tool_call_id": "tool_call_1",
                    "tool_name": "read_file",
                    "turn": 1,
                    "tool_arguments": '{"path":"README.md"}',
                }
            )
            callback(
                {
                    "kind": "tool",
                    "phase": "end",
                    "runtime_id": "tool_call_1",
                    "tool_call_id": "tool_call_1",
                    "tool_name": "read_file",
                    "turn": 1,
                    "result": "# README",
                    "ok": True,
                }
            )
            callback(
                {
                    "kind": "llm",
                    "phase": "end",
                    "runtime_id": "llm_turn_1",
                    "provider_id": "xunfei",
                    "model": "provider/default-model",
                    "turn": 1,
                    "tool_result": '{"response_id":"resp_1"}',
                    "ok": True,
                }
            )
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

        assert "model_call_started" in event_types
        assert "model_call_completed" in event_types
        assert "tool_call_started" in event_types
        assert "tool_call_completed" in event_types

        model_start = next(event for event in events if event.event_type == "model_call_started")
        assert model_start.runtime_id == "llm_turn_1"
        assert model_start.turn == 1
        assert model_start.payload["provider_id"] == "xunfei"

        tool_end = next(event for event in events if event.event_type == "tool_call_completed")
        assert tool_end.runtime_id == "tool_call_1"
        assert tool_end.payload["tool_name"] == "read_file"
        assert tool_end.payload["result_raw"] == "# README"
    finally:
        settings.data_dir = original_data_dir
