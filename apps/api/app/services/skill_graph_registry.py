from __future__ import annotations

from app.schemas.skill_graph import (
    CapabilityDefinition,
    CompositeDefinition,
    GraphPlaybookDefinition,
)
from app.services.skill_registry import SkillRegistryService
from app.services.storage import (
    GRAPH_CAPABILITIES_NAMESPACE,
    GRAPH_COMPOSITES_NAMESPACE,
    GRAPH_PLAYBOOKS_NAMESPACE,
    JsonStorage,
)


class SkillGraphRegistryService:
    def __init__(self, storage: JsonStorage, skill_registry: SkillRegistryService) -> None:
        self.storage = storage
        self.skill_registry = skill_registry

    def list_capabilities(self) -> list[CapabilityDefinition]:
        return [
            CapabilityDefinition.model_validate(item)
            for item in self.storage.list_json(GRAPH_CAPABILITIES_NAMESPACE)
        ]

    def get_capability(self, capability_id: str) -> CapabilityDefinition:
        payload = self.storage.load_json(GRAPH_CAPABILITIES_NAMESPACE, capability_id)
        return CapabilityDefinition.model_validate(payload)

    def save_capability(self, capability: CapabilityDefinition) -> CapabilityDefinition:
        self.storage.save_json(
            GRAPH_CAPABILITIES_NAMESPACE,
            capability.id,
            capability.model_dump(mode="json"),
        )
        return capability

    def delete_capability(self, capability_id: str) -> None:
        references = self.find_capability_references(capability_id)
        if references["composites"] or references["playbooks"]:
            composite_refs = ", ".join(references["composites"])
            playbook_refs = ", ".join(references["playbooks"])
            parts = []
            if composite_refs:
                parts.append(f"composites: {composite_refs}")
            if playbook_refs:
                parts.append(f"playbooks: {playbook_refs}")
            raise ValueError(f"capability is still referenced by {'; '.join(parts)}")
        self.storage.delete_json(GRAPH_CAPABILITIES_NAMESPACE, capability_id)

    def find_capability_references(self, capability_id: str) -> dict[str, list[str]]:
        composites = sorted(
            composite.id
            for composite in self.list_composites()
            if any(node.capability_id == capability_id for node in composite.nodes)
        )
        playbooks = sorted(
            playbook.id
            for playbook in self.list_graph_playbooks()
            if any(node.capability_id == capability_id for node in playbook.nodes)
        )
        return {"composites": composites, "playbooks": playbooks}

    def list_composites(self) -> list[CompositeDefinition]:
        return [
            CompositeDefinition.model_validate(item)
            for item in self.storage.list_json(GRAPH_COMPOSITES_NAMESPACE)
        ]

    def get_composite(self, composite_id: str) -> CompositeDefinition:
        payload = self.storage.load_json(GRAPH_COMPOSITES_NAMESPACE, composite_id)
        return CompositeDefinition.model_validate(payload)

    def save_composite(self, composite: CompositeDefinition) -> CompositeDefinition:
        known_capabilities = {item.id for item in self.list_capabilities()}
        missing = sorted(
            {
                node.capability_id
                for node in composite.nodes
                if node.capability_id not in known_capabilities
            }
        )
        if missing:
            raise ValueError(f"composite references unknown capabilities: {', '.join(missing)}")
        self.storage.save_json(
            GRAPH_COMPOSITES_NAMESPACE,
            composite.id,
            composite.model_dump(mode="json"),
        )
        return composite

    def delete_composite(self, composite_id: str) -> None:
        playbook_refs = sorted(
            playbook.id
            for playbook in self.list_graph_playbooks()
            if any(node.composite_id == composite_id for node in playbook.nodes)
        )
        if playbook_refs:
            raise ValueError(
                "composite is still referenced by playbooks: " + ", ".join(playbook_refs)
            )
        self.storage.delete_json(GRAPH_COMPOSITES_NAMESPACE, composite_id)

    def list_graph_playbooks(self) -> list[GraphPlaybookDefinition]:
        return [
            GraphPlaybookDefinition.model_validate(item)
            for item in self.storage.list_json(GRAPH_PLAYBOOKS_NAMESPACE)
        ]

    def get_graph_playbook(self, graph_id: str) -> GraphPlaybookDefinition:
        payload = self.storage.load_json(GRAPH_PLAYBOOKS_NAMESPACE, graph_id)
        return GraphPlaybookDefinition.model_validate(payload)

    def save_graph_playbook(self, graph: GraphPlaybookDefinition) -> GraphPlaybookDefinition:
        known_composites = {item.id for item in self.list_composites()}
        known_capabilities = {item.id for item in self.list_capabilities()}
        missing_refs: set[str] = set()
        for node in graph.nodes:
            if node.composite_id and node.composite_id not in known_composites:
                missing_refs.add(node.composite_id)
            if node.capability_id and node.capability_id not in known_capabilities:
                missing_refs.add(node.capability_id)
        if missing_refs:
            refs = ", ".join(sorted(missing_refs))
            raise ValueError(f"graph playbook references unknown nodes: {refs}")
        self.storage.save_json(
            GRAPH_PLAYBOOKS_NAMESPACE,
            graph.id,
            graph.model_dump(mode="json"),
        )
        return graph

    def delete_graph_playbook(self, graph_id: str) -> None:
        self.storage.delete_json(GRAPH_PLAYBOOKS_NAMESPACE, graph_id)

    def sync_capability_from_skill(self, skill_name: str) -> CapabilityDefinition:
        capability = self.skill_registry.build_capability_definition(skill_name)
        return self.save_capability(capability)
