from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.schemas.skill_graph import (
    GraphApprovalDecision,
    GraphRun,
    GraphRunNodeState,
    transition_graph_run,
)
from app.services.skill_graph_actions import GraphActionError, GraphActionHandler
from app.services.skill_graph_registry import SkillGraphRegistryService
from app.services.storage import GRAPH_RUNS_NAMESPACE, JsonStorage


class SkillGraphRunner:
    def __init__(
        self,
        *,
        storage: JsonStorage,
        registry: SkillGraphRegistryService,
        action_handlers: dict[str, GraphActionHandler],
    ) -> None:
        self.storage = storage
        self.registry = registry
        self.action_handlers = action_handlers

    def start_run(self, graph_playbook_id: str, input_payload: dict[str, Any]) -> GraphRun:
        graph = self.registry.get_graph_playbook(graph_playbook_id)
        run = GraphRun(
            id=f"run_{uuid4().hex[:12]}",
            graph_playbook_id=graph_playbook_id,
            status="pending",
            input_payload=input_payload,
        )
        self._persist_run(run, "created")
        return self._continue_run(run, graph, graph.entry_node_id)

    def get_run(self, run_id: str) -> GraphRun:
        payload = self.storage.load_json(GRAPH_RUNS_NAMESPACE, run_id)
        return GraphRun.model_validate(payload)

    def record_approval(
        self,
        run_id: str,
        approval_id: str,
        *,
        approved: bool,
        decided_by: str,
        comment: str | None = None,
    ) -> GraphRun:
        run = self.get_run(run_id)
        graph = self.registry.get_graph_playbook(run.graph_playbook_id)
        if run.status != "waiting_for_human":
            raise ValueError(f"run {run_id} is not waiting for human input")

        decision_status = "approved" if approved else "rejected"
        approvals = []
        approval_node_id: str | None = None
        for approval in run.approvals:
            if approval.approval_id == approval_id:
                approval_node_id = approval.node_id
                approvals.append(
                    approval.model_copy(
                        update={
                            "status": decision_status,
                            "decided_by": decided_by,
                            "decided_at": datetime.utcnow(),
                            "comment": comment,
                        }
                    )
                )
            else:
                approvals.append(approval)
        if approval_node_id is None:
            raise FileNotFoundError(approval_id)

        node_states = [
            state.model_copy(update={"status": "succeeded", "finished_at": datetime.utcnow()})
            if state.node_id == approval_node_id
            else state
            for state in run.node_states
        ]
        resumed = run.model_copy(update={"approvals": approvals, "node_states": node_states})
        resumed = transition_graph_run(resumed, "running")
        self._persist_run(resumed, "approval-recorded")

        next_node_id = self._next_node_id(graph, approval_node_id, "approve" if approved else "reject")
        if next_node_id is None:
            finished = transition_graph_run(resumed, "succeeded")
            finished = finished.model_copy(update={"current_node_id": None})
            self._persist_run(finished, "completed")
            return finished
        return self._continue_run(resumed, graph, next_node_id)

    def _continue_run(self, run: GraphRun, graph, next_node_id: str) -> GraphRun:
        active = run if run.status == "running" else transition_graph_run(run, "running")
        current_node_id: str | None = next_node_id
        while current_node_id is not None:
            node = next(node for node in graph.nodes if node.id == current_node_id)
            active = active.model_copy(update={"current_node_id": node.id})
            if node.type == "human_approval":
                waiting = self._pause_for_approval(active, node.id)
                self._persist_run(waiting, "waiting-for-human")
                return waiting

            state = self._get_or_create_node_state(active, node.id)
            running_state = state.model_copy(
                update={"status": "running", "attempts": state.attempts + 1, "started_at": datetime.utcnow()}
            )
            active = self._replace_node_state(active, running_state)
            self._persist_run(active, f"node-{node.id}-running")
            try:
                output = self._execute_node(graph, active, node)
            except GraphActionError as error:
                failed_state = running_state.model_copy(
                    update={"status": "failed", "finished_at": datetime.utcnow(), "error": str(error)}
                )
                failed_run = self._replace_node_state(active, failed_state)
                failed_run = transition_graph_run(failed_run, "failed")
                self._persist_run(failed_run, f"node-{node.id}-failed")
                return failed_run

            succeeded_state = running_state.model_copy(
                update={"status": "succeeded", "finished_at": datetime.utcnow(), "output": output, "error": None}
            )
            merged_output = dict(active.output_payload)
            merged_output.update(output)
            active = self._replace_node_state(active, succeeded_state)
            active = active.model_copy(update={"output_payload": merged_output})
            self._persist_run(active, f"node-{node.id}-succeeded")
            current_node_id = self._next_node_id(graph, node.id, None)

        finished = transition_graph_run(active, "succeeded")
        finished = finished.model_copy(update={"current_node_id": None})
        self._persist_run(finished, "completed")
        return finished

    def _execute_node(self, graph, run: GraphRun, node) -> dict[str, Any]:
        if node.type == "capability":
            capability = self.registry.get_capability(node.capability_id)
            return self._run_capability(capability.action, capability.retry_policy.max_attempts, run)

        composite = self.registry.get_composite(node.composite_id)
        state = dict(run.output_payload)
        for composite_node in sorted(composite.nodes, key=lambda item: item.order):
            capability = self.registry.get_capability(composite_node.capability_id)
            result = self._run_capability(capability.action, capability.retry_policy.max_attempts, run, state)
            state.update(result)
        return state

    def _run_capability(
        self,
        action: str,
        max_attempts: int,
        run: GraphRun,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        handler = self.action_handlers.get(action)
        if handler is None:
            raise GraphActionError(f"no action handler registered for {action}")
        last_error: GraphActionError | None = None
        for _ in range(max_attempts):
            try:
                return handler({"input": run.input_payload, "state": state or dict(run.output_payload)}, run.input_payload)
            except GraphActionError as error:
                last_error = error
                if not error.retryable:
                    raise
        assert last_error is not None
        raise last_error

    def _pause_for_approval(self, run: GraphRun, node_id: str) -> GraphRun:
        approval = GraphApprovalDecision(
            approval_id=f"approval_{uuid4().hex[:10]}",
            node_id=node_id,
            status="pending",
        )
        state = self._get_or_create_node_state(run, node_id).model_copy(
            update={"status": "waiting_for_human", "started_at": datetime.utcnow()}
        )
        waiting = self._replace_node_state(run, state)
        waiting = waiting.model_copy(update={"approvals": [*waiting.approvals, approval]})
        return transition_graph_run(waiting, "waiting_for_human")

    def _replace_node_state(self, run: GraphRun, state: GraphRunNodeState) -> GraphRun:
        replaced = False
        node_states: list[GraphRunNodeState] = []
        for existing in run.node_states:
            if existing.node_id == state.node_id:
                node_states.append(state)
                replaced = True
            else:
                node_states.append(existing)
        if not replaced:
            node_states.append(state)
        return run.model_copy(update={"node_states": node_states, "updated_at": datetime.utcnow()})

    def _get_or_create_node_state(self, run: GraphRun, node_id: str) -> GraphRunNodeState:
        for state in run.node_states:
            if state.node_id == node_id:
                return state
        return GraphRunNodeState(node_id=node_id, status="pending")

    def _next_node_id(self, graph, source_node_id: str, condition: str | None) -> str | None:
        edges = [edge for edge in graph.edges if edge.source == source_node_id]
        if condition is not None:
            for edge in edges:
                if edge.condition == condition:
                    return edge.target
            return None
        for edge in edges:
            if edge.condition in (None, ""):
                return edge.target
        return None

    def _persist_run(self, run: GraphRun, snapshot_name: str) -> None:
        payload = run.model_dump(mode="json")
        self.storage.save_json(GRAPH_RUNS_NAMESPACE, run.id, payload)
        self.storage.save_graph_run_snapshot(run.id, snapshot_name, payload)
