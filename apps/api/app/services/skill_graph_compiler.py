from __future__ import annotations

from collections import defaultdict, deque

from app.schemas.skill_graph import CompositeDefinition, GraphCompileResult, GraphPlaybookDefinition


class SkillGraphCompiler:
    def __init__(self, composite_warning_threshold: int = 10) -> None:
        self.composite_warning_threshold = composite_warning_threshold

    def compile_composite(self, composite: CompositeDefinition) -> GraphCompileResult:
        errors: list[str] = []
        if composite.mode == "chain":
            orders = [node.order for node in composite.nodes]
            if len(orders) != len(set(orders)):
                errors.append("chain composite contains duplicate execution order values")
            if orders:
                expected = list(range(1, len(orders) + 1))
                if sorted(orders) != expected:
                    errors.append("chain composite must use contiguous order values starting at 1")
        return GraphCompileResult(ok=not errors, errors=errors, warnings=[])

    def compile_graph_playbook(self, graph: GraphPlaybookDefinition) -> GraphCompileResult:
        errors: list[str] = []
        warnings: list[str] = []
        node_ids = {node.id for node in graph.nodes}

        if graph.entry_node_id not in node_ids:
            errors.append("graph entry node must exist")

        adjacency: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for edge in graph.edges:
            adjacency[edge.source].append((edge.target, edge.condition))

        if graph.entry_node_id in node_ids:
            reachable = self._walk(graph.entry_node_id, adjacency)
            unreachable = sorted(node_ids - reachable)
            if unreachable:
                errors.append(f"graph contains unreachable nodes: {', '.join(unreachable)}")

        for node in graph.nodes:
            if node.type != "human_approval":
                continue
            conditions = {condition or "" for _, condition in adjacency.get(node.id, [])}
            if not {"approve", "reject"}.issubset(conditions):
                errors.append(
                    f"human approval node '{node.id}' must define approve/reject exits"
                )

        composite_nodes = [node for node in graph.nodes if node.type == "composite"]
        if len(composite_nodes) > self.composite_warning_threshold:
            warnings.append(
                "graph composite count exceeds recommended threshold "
                f"({len(composite_nodes)} > {self.composite_warning_threshold})"
            )

        return GraphCompileResult(
            ok=not errors,
            errors=errors,
            warnings=warnings,
            normalized_definition=graph if not errors else None,
        )

    def _walk(
        self,
        entry_node_id: str,
        adjacency: dict[str, list[tuple[str, str | None]]],
    ) -> set[str]:
        visited: set[str] = set()
        queue: deque[str] = deque([entry_node_id])
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            for target, _ in adjacency.get(node_id, []):
                if target not in visited:
                    queue.append(target)
        return visited
