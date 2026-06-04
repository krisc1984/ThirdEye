from app.schemas.skill_graph import (
    CompositeDefinition,
    CompositeNodeDefinition,
    GraphEdgeDefinition,
    GraphNodeDefinition,
    GraphPlaybookDefinition,
)
from app.services.skill_graph_compiler import SkillGraphCompiler


def test_rejects_cyclic_chain_composites():
    composite = CompositeDefinition.model_construct(
        id="comp_bad",
        name="Bad",
        mode="chain",
        nodes=[
            CompositeNodeDefinition.model_construct(
                id="step_a",
                capability_id="cap_fetch_page",
                order=1,
            ),
            CompositeNodeDefinition.model_construct(
                id="step_b",
                capability_id="cap_summarize_page",
                order=1,
            ),
        ],
    )

    result = SkillGraphCompiler().compile_composite(composite)

    assert not result.ok
    assert any("chain composite" in error for error in result.errors)


def test_rejects_graph_playbooks_with_missing_entry_nodes():
    graph = GraphPlaybookDefinition.model_construct(
        id="graph_missing_entry",
        name="Missing Entry",
        version="1.0.0",
        entry_node_id="missing",
        nodes=[
            GraphNodeDefinition.model_construct(
                id="start",
                type="composite",
                composite_id="comp_monitor",
            )
        ],
        edges=[],
    )

    result = SkillGraphCompiler().compile_graph_playbook(graph)

    assert not result.ok
    assert any("entry node" in error for error in result.errors)


def test_rejects_unreachable_graph_nodes():
    graph = GraphPlaybookDefinition(
        id="graph_unreachable",
        name="Unreachable",
        version="1.0.0",
        entry_node_id="start",
        nodes=[
            {"id": "start", "type": "composite", "composite_id": "comp_monitor"},
            {"id": "finish", "type": "composite", "composite_id": "comp_monitor"},
            {"id": "orphan", "type": "composite", "composite_id": "comp_monitor"},
        ],
        edges=[GraphEdgeDefinition(source="start", target="finish")],
    )

    result = SkillGraphCompiler().compile_graph_playbook(graph)

    assert not result.ok
    assert any("unreachable" in error for error in result.errors)


def test_requires_approve_and_reject_edges_for_human_approval_nodes():
    graph = GraphPlaybookDefinition(
        id="graph_approval_bad",
        name="Approval",
        version="1.0.0",
        entry_node_id="review",
        nodes=[
            {"id": "review", "type": "human_approval", "approval_label": "Review Draft"},
            {"id": "approved", "type": "composite", "composite_id": "comp_monitor"},
        ],
        edges=[GraphEdgeDefinition(source="review", target="approved", condition="approve")],
    )

    result = SkillGraphCompiler().compile_graph_playbook(graph)

    assert not result.ok
    assert any("approve/reject" in error for error in result.errors)


def test_warns_when_composite_count_exceeds_threshold():
    graph = GraphPlaybookDefinition(
        id="graph_warning",
        name="Warning",
        version="1.0.0",
        entry_node_id="node_1",
        nodes=[
            {"id": f"node_{index}", "type": "composite", "composite_id": f"comp_{index}"}
            for index in range(1, 5)
        ],
        edges=[
            GraphEdgeDefinition(source="node_1", target="node_2"),
            GraphEdgeDefinition(source="node_2", target="node_3"),
            GraphEdgeDefinition(source="node_3", target="node_4"),
        ],
    )

    result = SkillGraphCompiler(composite_warning_threshold=3).compile_graph_playbook(graph)

    assert result.ok
    assert any("composite" in warning for warning in result.warnings)
    assert result.normalized_definition is not None
