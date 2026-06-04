from app.schemas.skill_graph import CapabilityDefinition, CompositeDefinition, GraphPlaybookDefinition
from app.services.skill_graph_actions import TransientGraphActionError
from app.services.skill_graph_registry import SkillGraphRegistryService
from app.services.skill_graph_runner import SkillGraphRunner
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage


def _make_registry(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    return storage, registry


def test_successful_chain_composite_execution(tmp_path):
    storage, registry = _make_registry(tmp_path)
    registry.save_capability(
        CapabilityDefinition(id="cap_fetch", name="Fetch", kind="tool", action="fetch")
    )
    registry.save_capability(
        CapabilityDefinition(id="cap_render", name="Render", kind="tool", action="render")
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_report",
            name="Report",
            mode="chain",
            nodes=[
                {"id": "fetch", "capability_id": "cap_fetch", "order": 1},
                {"id": "render", "capability_id": "cap_render", "order": 2},
            ],
        )
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_report",
            name="Report",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "composite", "composite_id": "comp_report"}],
            edges=[],
        )
    )

    runner = SkillGraphRunner(
        storage=storage,
        registry=registry,
        action_handlers={
            "fetch": lambda ctx, _: {"page": ctx["input"]["url"]},
            "render": lambda ctx, _: {"report": f"report:{ctx['state']['page']}"},
        },
    )

    run = runner.start_run("graph_report", {"url": "https://example.com"})

    assert run.status == "succeeded"
    assert run.output_payload["report"] == "report:https://example.com"


def test_capability_retry_policy_on_transient_failure(tmp_path):
    storage, registry = _make_registry(tmp_path)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_flaky",
            name="Flaky",
            kind="tool",
            action="flaky",
            retry_policy={"max_attempts": 2, "retry_on": ["transient"]},
        )
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_flaky",
            name="Flaky",
            mode="chain",
            nodes=[{"id": "flaky", "capability_id": "cap_flaky", "order": 1}],
        )
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_flaky",
            name="Flaky",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "composite", "composite_id": "comp_flaky"}],
            edges=[],
        )
    )

    attempts = {"count": 0}

    def flaky_action(_ctx, _payload):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TransientGraphActionError("try again")
        return {"status": "ok"}

    runner = SkillGraphRunner(storage=storage, registry=registry, action_handlers={"flaky": flaky_action})

    run = runner.start_run("graph_flaky", {})

    assert run.status == "succeeded"
    assert attempts["count"] == 2


def test_graph_pauses_at_human_approval(tmp_path):
    storage, registry = _make_registry(tmp_path)
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_approval",
            name="Approval",
            version="1.0.0",
            entry_node_id="review",
            nodes=[{"id": "review", "type": "human_approval", "approval_label": "Review draft"}],
            edges=[],
        )
    )

    runner = SkillGraphRunner(storage=storage, registry=registry, action_handlers={})

    run = runner.start_run("graph_approval", {})

    assert run.status == "waiting_for_human"
    assert run.approvals[0].status == "pending"


def test_graph_resumes_from_approval(tmp_path):
    storage, registry = _make_registry(tmp_path)
    registry.save_capability(
        CapabilityDefinition(id="cap_render", name="Render", kind="tool", action="render")
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_approval_resume",
            name="Approval Resume",
            version="1.0.0",
            entry_node_id="review",
            nodes=[
                {"id": "review", "type": "human_approval", "approval_label": "Review draft"},
                {"id": "publish", "type": "capability", "capability_id": "cap_render"},
            ],
            edges=[{"source": "review", "target": "publish", "condition": "approve"}],
        )
    )

    runner = SkillGraphRunner(
        storage=storage,
        registry=registry,
        action_handlers={"render": lambda _ctx, _payload: {"published": True}},
    )

    run = runner.start_run("graph_approval_resume", {})
    resumed = runner.record_approval(run.id, run.approvals[0].approval_id, approved=True, decided_by="tester")

    assert resumed.status == "succeeded"
    assert resumed.output_payload["published"] is True


def test_graph_fails_when_capability_exhausts_retries(tmp_path):
    storage, registry = _make_registry(tmp_path)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fail",
            name="Fail",
            kind="tool",
            action="fail",
            retry_policy={"max_attempts": 2, "retry_on": ["transient"]},
        )
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_fail",
            name="Fail",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "capability", "capability_id": "cap_fail"}],
            edges=[],
        )
    )

    runner = SkillGraphRunner(
        storage=storage,
        registry=registry,
        action_handlers={"fail": lambda _ctx, _payload: (_ for _ in ()).throw(TransientGraphActionError("still bad"))},
    )

    run = runner.start_run("graph_fail", {})

    assert run.status == "failed"
    assert run.node_states[0].status == "failed"
