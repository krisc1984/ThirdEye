import pytest
from pydantic import ValidationError

from app.schemas.skill_graph import (
    CapabilityDefinition,
    CompositeDefinition,
    CompositeNodeDefinition,
    GraphApprovalDecision,
    GraphEdgeDefinition,
    GraphPlaybookDefinition,
    GraphRun,
    GraphRunNodeState,
    transition_graph_run,
)


def test_capability_kind_is_limited():
    capability = CapabilityDefinition(
        id="cap_fetch_page",
        name="Fetch Page",
        kind="tool",
        action="fetch_page",
    )

    assert capability.kind == "tool"

    with pytest.raises(ValidationError):
        CapabilityDefinition(
            id="cap_bad",
            name="Bad",
            kind="workflow",
            action="bad_action",
        )


def test_chain_composite_requires_chain_mode():
    composite = CompositeDefinition(
        id="comp_monitor",
        name="Monitor",
        mode="chain",
        nodes=[
            CompositeNodeDefinition(
                id="node_fetch",
                capability_id="cap_fetch_page",
                order=1,
            )
        ],
    )

    assert composite.mode == "chain"

    with pytest.raises(ValidationError):
        CompositeDefinition(
            id="comp_bad",
            name="Bad",
            mode="fanout",
            nodes=[],
        )


def test_graph_node_type_is_limited():
    graph = GraphPlaybookDefinition(
        id="graph_weekly_report",
        name="Weekly Report",
        version="1.2.3",
        entry_node_id="start",
        nodes=[
            {
                "id": "start",
                "type": "composite",
                "composite_id": "comp_monitor",
            }
        ],
        edges=[],
    )

    assert graph.nodes[0].type == "composite"

    with pytest.raises(ValidationError):
        GraphPlaybookDefinition(
            id="graph_bad",
            name="Bad",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "decision"}],
            edges=[],
        )


def test_graph_version_requires_semver():
    with pytest.raises(ValidationError):
        GraphPlaybookDefinition(
            id="graph_version_bad",
            name="Bad",
            version="v1",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "composite", "composite_id": "comp_monitor"}],
            edges=[],
        )


def test_graph_complexity_guardrails():
    with pytest.raises(ValidationError):
        GraphPlaybookDefinition(
            id="graph_too_large",
            name="Too Large",
            version="1.0.0",
            entry_node_id="node_0",
            nodes=[
                {
                    "id": f"node_{index}",
                    "type": "composite",
                    "composite_id": "comp_monitor",
                }
                for index in range(26)
            ],
            edges=[
                GraphEdgeDefinition(
                    source=f"node_{index}",
                    target=f"node_{index + 1}",
                )
                for index in range(25)
            ],
        )


def test_graph_run_status_transitions():
    run = GraphRun(
        id="run_1",
        graph_playbook_id="graph_weekly_report",
        status="pending",
        node_states=[
            GraphRunNodeState(
                node_id="start",
                status="pending",
            )
        ],
        approvals=[
            GraphApprovalDecision(
                approval_id="approval_1",
                node_id="approve_report",
                status="pending",
            )
        ],
    )

    queued = transition_graph_run(run, "running")
    waiting = transition_graph_run(queued, "waiting_for_human")
    resumed = transition_graph_run(waiting, "running")
    completed = transition_graph_run(resumed, "succeeded")

    assert completed.status == "succeeded"

    with pytest.raises(ValueError):
        transition_graph_run(completed, "running")
