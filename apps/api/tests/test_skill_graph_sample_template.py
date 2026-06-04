from pathlib import Path

from app.services.skill_graph_compiler import SkillGraphCompiler
from app.services.skill_graph_registry import SkillGraphRegistryService
from app.services.skill_graph_runner import SkillGraphRunner
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage


def test_sample_graph_compiles_loads_and_pauses_for_approval():
    repo_data_root = Path(__file__).resolve().parents[3] / "data"
    storage = JsonStorage(repo_data_root)
    registry = SkillGraphRegistryService(storage, SkillRegistryService(storage, repo_data_root / "skills"))

    capabilities = registry.list_capabilities()
    composites = registry.list_composites()
    playbooks = registry.list_graph_playbooks()

    assert any(item.id == "cap_fetch_competitor_homepage" for item in capabilities)
    assert any(item.id == "comp_single_competitor_monitor" for item in composites)
    graph = next(item for item in playbooks if item.id == "graph_weekly_competitor_report")

    compile_result = SkillGraphCompiler().compile_graph_playbook(graph)
    assert compile_result.ok is True

    runner = SkillGraphRunner(
        storage=storage,
        registry=registry,
        action_handlers={
            "fetch_competitor_homepage": lambda _ctx, payload: {
                "homepage_html": f"<html>{payload.get('competitor', 'unknown')}</html>"
            },
            "summarize_page_changes": lambda ctx, _payload: {
                "summary": f"summary:{ctx['state'].get('homepage_html', '')}"
            },
            "render_weekly_report": lambda ctx, payload: {
                "published": True,
                "report": f"weekly-report:{payload.get('competitor', ctx['state'].get('summary', 'ready'))}",
            },
        },
    )

    run = runner.start_run("graph_weekly_competitor_report", {"competitor": "Acme"})

    assert run.status == "waiting_for_human"
    assert run.current_node_id == "approve_report"
    assert run.approvals[0].status == "pending"
