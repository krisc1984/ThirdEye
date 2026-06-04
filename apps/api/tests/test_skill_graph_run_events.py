from app.schemas.skill_graph import GraphRun, GraphRunNodeState
from app.services.skill_graph_run_events import SkillGraphRunEventService
from app.services.storage import JsonStorage


def test_run_events_are_appended_in_order(tmp_path):
    storage = JsonStorage(tmp_path)
    events = SkillGraphRunEventService(storage)

    first = events.append_run_event(
        GraphRun(id="run_1", graph_playbook_id="graph_1", status="running"),
        event_type="run_updated",
    )
    second = events.append_run_event(
        GraphRun(id="run_1", graph_playbook_id="graph_1", status="waiting_for_human"),
        event_type="approval_requested",
    )

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert [item["event_type"] for item in events.list_run_events("run_1")] == [
        "run_updated",
        "approval_requested",
    ]


def test_event_payload_includes_status_and_node_state(tmp_path):
    storage = JsonStorage(tmp_path)
    events = SkillGraphRunEventService(storage)
    run = GraphRun(
        id="run_2",
        graph_playbook_id="graph_2",
        status="running",
        node_states=[GraphRunNodeState(node_id="start", status="running")],
    )

    event = events.append_run_event(run, event_type="node_updated")

    assert event["payload"]["status"] == "running"
    assert event["payload"]["node_state"]["node_id"] == "start"


def test_event_stream_can_replay_latest_run_snapshot(tmp_path):
    storage = JsonStorage(tmp_path)
    events = SkillGraphRunEventService(storage)
    run = GraphRun(id="run_3", graph_playbook_id="graph_3", status="succeeded")

    events.append_run_event(run, event_type="run_updated")
    replay = events.replay_run_snapshot("run_3")

    assert replay["event_type"] == "snapshot"
    assert replay["payload"]["status"] == "succeeded"
