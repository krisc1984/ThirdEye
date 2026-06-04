from pathlib import Path

import pytest

from app.schemas.skill_graph import CapabilityDefinition, CompositeDefinition, GraphPlaybookDefinition
from app.services.skill_graph_registry import SkillGraphRegistryService
from app.services.skill_registry import SkillRegistryService
from app.services.storage import JsonStorage


def _write_skill(skills_root: Path, name: str, description: str) -> None:
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_register_capability(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)

    capability = registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )

    assert registry.get_capability("cap_fetch_page") == capability
    assert [item.id for item in registry.list_capabilities()] == ["cap_fetch_page"]


def test_register_composite(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )

    composite = registry.save_composite(
        CompositeDefinition(
            id="comp_monitor",
            name="Monitor",
            mode="chain",
            nodes=[{"id": "fetch", "capability_id": "cap_fetch_page", "order": 1}],
        )
    )

    assert registry.get_composite("comp_monitor") == composite


def test_register_graph_playbook(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_monitor",
            name="Monitor",
            mode="chain",
            nodes=[{"id": "fetch", "capability_id": "cap_fetch_page", "order": 1}],
        )
    )

    graph = registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_report",
            name="Report",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "composite", "composite_id": "comp_monitor"}],
            edges=[],
        )
    )

    assert registry.get_graph_playbook("graph_report") == graph


def test_reject_missing_capability_references(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)

    with pytest.raises(ValueError):
        registry.save_composite(
            CompositeDefinition(
                id="comp_bad",
                name="Bad",
                mode="chain",
                nodes=[{"id": "fetch", "capability_id": "cap_missing", "order": 1}],
            )
        )


def test_derive_capability_from_enabled_skill_registry_entry(tmp_path):
    skills_root = tmp_path / "skills"
    _write_skill(skills_root, "competitor-watch", "Watch competitor changes")

    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, skills_root)
    registry = SkillGraphRegistryService(storage, skill_registry)

    derived = registry.sync_capability_from_skill("competitor-watch")

    assert derived.kind == "skill"
    assert derived.action == "competitor-watch"
    assert derived.name == "competitor-watch"
    assert "Watch competitor changes" in derived.description


def test_delete_capability_rejects_existing_references(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_monitor",
            name="Monitor",
            mode="chain",
            nodes=[{"id": "fetch", "capability_id": "cap_fetch_page", "order": 1}],
        )
    )

    with pytest.raises(ValueError, match="still referenced"):
        registry.delete_capability("cap_fetch_page")


def test_delete_capability_when_unreferenced(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )

    registry.delete_capability("cap_fetch_page")

    with pytest.raises(FileNotFoundError):
        registry.get_capability("cap_fetch_page")


def test_delete_composite_rejects_existing_playbook_references(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_monitor",
            name="Monitor",
            mode="chain",
            nodes=[{"id": "fetch", "capability_id": "cap_fetch_page", "order": 1}],
        )
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_report",
            name="Report",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "composite", "composite_id": "comp_monitor"}],
            edges=[],
        )
    )

    with pytest.raises(ValueError, match="still referenced"):
        registry.delete_composite("comp_monitor")


def test_delete_composite_when_unreferenced(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )
    registry.save_composite(
        CompositeDefinition(
            id="comp_monitor",
            name="Monitor",
            mode="chain",
            nodes=[{"id": "fetch", "capability_id": "cap_fetch_page", "order": 1}],
        )
    )

    registry.delete_composite("comp_monitor")

    with pytest.raises(FileNotFoundError):
        registry.get_composite("comp_monitor")


def test_delete_graph_playbook_when_unreferenced(tmp_path):
    storage = JsonStorage(tmp_path)
    skill_registry = SkillRegistryService(storage, tmp_path / "skills")
    registry = SkillGraphRegistryService(storage, skill_registry)
    registry.save_capability(
        CapabilityDefinition(
            id="cap_fetch_page",
            name="Fetch Page",
            kind="tool",
            action="fetch_page",
        )
    )
    registry.save_graph_playbook(
        GraphPlaybookDefinition(
            id="graph_report",
            name="Report",
            version="1.0.0",
            entry_node_id="start",
            nodes=[{"id": "start", "type": "capability", "capability_id": "cap_fetch_page"}],
            edges=[],
        )
    )

    registry.delete_graph_playbook("graph_report")

    with pytest.raises(FileNotFoundError):
        registry.get_graph_playbook("graph_report")
