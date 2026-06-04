from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CapabilityKind = Literal["tool", "skill", "agent", "service"]
CapabilitySourceType = Literal["skill", "agent", "tool", "mcp_server"]
CompositeMode = Literal["chain"]
GraphNodeType = Literal["composite", "capability", "human_approval"]
GraphRunStatus = Literal[
    "pending",
    "running",
    "waiting_for_human",
    "succeeded",
    "failed",
    "cancelled",
]
GraphNodeRunStatus = Literal[
    "pending",
    "running",
    "waiting_for_human",
    "succeeded",
    "failed",
    "skipped",
]
GraphApprovalStatus = Literal["pending", "approved", "rejected"]
GraphEventType = Literal["run_updated", "node_updated", "approval_requested", "approval_recorded"]

MAX_GRAPH_NODES = 25
MAX_GRAPH_EDGES = 50
_SEMVER_PARTS = 3
_GRAPH_RUN_TRANSITIONS: dict[GraphRunStatus, set[GraphRunStatus]] = {
    "pending": {"running", "cancelled"},
    "running": {"waiting_for_human", "succeeded", "failed", "cancelled"},
    "waiting_for_human": {"running", "failed", "cancelled"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
}


def _validate_semver(value: str) -> str:
    parts = value.split(".")
    if len(parts) != _SEMVER_PARTS or any(not part.isdigit() for part in parts):
        raise ValueError("version must use semantic version format, e.g. 1.0.0")
    return value


class CapabilityRetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=5)
    backoff_seconds: float = Field(default=0.0, ge=0.0, le=300.0)
    retry_on: list[str] = Field(default_factory=list)


class CapabilitySourceReference(BaseModel):
    source_type: CapabilitySourceType
    source_id: str
    source_name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilitySourceDescriptor(BaseModel):
    source_type: CapabilitySourceType
    source_id: str
    name: str
    description: str = ""
    suggested_kind: CapabilityKind
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityDefinition(BaseModel):
    id: str
    name: str
    kind: CapabilityKind
    action: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    retry_policy: CapabilityRetryPolicy = Field(default_factory=CapabilityRetryPolicy)
    enabled: bool = True
    source: CapabilitySourceReference | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CapabilityDraftRequest(BaseModel):
    kind: CapabilityKind
    name: str
    description: str = ""
    provider_id: str | None = None
    source_type: CapabilitySourceType | None = None
    source_id: str | None = None


class CapabilityDraftResponse(BaseModel):
    capability: CapabilityDefinition
    execution_mode: Literal["deterministic", "llm"]
    resolved_provider_id: str | None = None
    execution_note: str | None = None


class CompositeNodeDefinition(BaseModel):
    id: str
    capability_id: str
    order: int = Field(ge=1)
    input_mapping: dict[str, Any] = Field(default_factory=dict)


class CompositeDefinition(BaseModel):
    id: str
    name: str
    mode: CompositeMode
    description: str = ""
    nodes: list[CompositeNodeDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_chain_nodes(self) -> "CompositeDefinition":
        seen_orders = set()
        for node in self.nodes:
            if node.order in seen_orders:
                raise ValueError("chain composite node order must be unique")
            seen_orders.add(node.order)
        return self


class GraphNodeDefinition(BaseModel):
    id: str
    type: GraphNodeType
    capability_id: str | None = None
    composite_id: str | None = None
    approval_label: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target_reference(self) -> "GraphNodeDefinition":
        if self.type == "capability" and not self.capability_id:
            raise ValueError("capability nodes require capability_id")
        if self.type == "composite" and not self.composite_id:
            raise ValueError("composite nodes require composite_id")
        if self.type == "human_approval" and not self.approval_label:
            self.approval_label = self.id
        return self


class GraphEdgeDefinition(BaseModel):
    source: str
    target: str
    condition: str | None = None


class GraphPlaybookDefinition(BaseModel):
    id: str
    name: str
    version: str
    description: str = ""
    entry_node_id: str
    nodes: list[GraphNodeDefinition] = Field(default_factory=list)
    edges: list[GraphEdgeDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return _validate_semver(value)

    @model_validator(mode="after")
    def validate_complexity(self) -> "GraphPlaybookDefinition":
        if len(self.nodes) > MAX_GRAPH_NODES:
            raise ValueError(f"graph exceeds node limit of {MAX_GRAPH_NODES}")
        if len(self.edges) > MAX_GRAPH_EDGES:
            raise ValueError(f"graph exceeds edge limit of {MAX_GRAPH_EDGES}")
        node_ids = {node.id for node in self.nodes}
        if self.entry_node_id not in node_ids:
            raise ValueError("entry node must exist in graph nodes")
        return self


class GraphCompileResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_definition: GraphPlaybookDefinition | None = None


class GraphRunNodeState(BaseModel):
    node_id: str
    status: GraphNodeRunStatus
    attempts: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class GraphApprovalDecision(BaseModel):
    approval_id: str
    node_id: str
    status: GraphApprovalStatus
    decided_by: str | None = None
    decided_at: datetime | None = None
    comment: str | None = None


class GraphRun(BaseModel):
    id: str
    graph_playbook_id: str
    status: GraphRunStatus
    node_states: list[GraphRunNodeState] = Field(default_factory=list)
    approvals: list[GraphApprovalDecision] = Field(default_factory=list)
    current_node_id: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GraphEvent(BaseModel):
    event_id: str
    run_id: str
    event_type: GraphEventType
    status: GraphRunStatus
    node_state: GraphRunNodeState | None = None
    approval: GraphApprovalDecision | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


def transition_graph_run(run: GraphRun, next_status: GraphRunStatus) -> GraphRun:
    allowed = _GRAPH_RUN_TRANSITIONS[run.status]
    if next_status not in allowed:
        raise ValueError(f"invalid graph run transition: {run.status} -> {next_status}")
    return run.model_copy(update={"status": next_status, "updated_at": datetime.utcnow()})
