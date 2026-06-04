export type Project = {
  id: string;
  name: string;
  root_path: string;
  knowledge_root_path?: string | null;
  slug: string;
  languages: string[];
  frameworks: string[];
  created_at: string;
};

export type ProjectScanSummary = {
  root_path: string;
  total_files: number;
  scanned_files: number;
  skipped_files: number;
  languages: Record<string, number>;
  docs: string[];
  tests: string[];
  config_files: string[];
  entrypoint_candidates: string[];
  sensitive_warnings: string[];
};

export type PlaybookMetadata = {
  id: string;
  project_id: string;
  name: string;
  version: string;
  status: "draft" | "active" | "archived";
  execution_mode: "deterministic" | "llm";
  orchestration_mode?: "playbook" | "project_skill_agent";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
  skill_path: string;
  agent_skill_path?: string | null;
  rules_path: string;
  evidence_path: string;
  created_at: string;
};

export type PlaybookRule = {
  id: string;
  category: string;
  name: string;
  default_severity: "blocker" | "major" | "minor" | "nit";
  applicability: string[];
  description: string;
  evidence_ids: string[];
  failure_modes: string[];
  review_prompts: string[];
  enabled: boolean;
};

export type EvidenceItem = {
  id: string;
  project_id: string;
  source_type: "code" | "doc" | "test" | "config" | "example";
  path: string;
  symbol?: string | null;
  summary: string;
  evidence_level: "confirmed" | "inferred" | "preference" | "unknown";
  metadata: Record<string, string>;
};

export type PlaybookDetail = {
  metadata: PlaybookMetadata;
  skill_markdown: string;
  project_summary: string;
  rules: PlaybookRule[];
  evidence: EvidenceItem[];
};

export type ModelProviderConfig = {
  id: string;
  name: string;
  provider_type: "openai" | "openai_compatible";
  model: string;
  api_key?: string | null;
  base_url?: string | null;
  api_shape: "responses" | "chat_completions";
  timeout_seconds?: number;
  max_retries?: number;
  tracing_enabled?: boolean;
};

export type BusinessAgentConfig = {
  id: string;
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  status: "active" | "draft";
  is_default: boolean;
};

export type McpServerEnvVar = {
  key: string;
  value: string;
};

export type McpServerConfig = {
  id: string;
  name: string;
  description: string;
  transport: "stdio" | "streamable_http" | "sse";
  scope: "global" | "project";
  status: "connected" | "idle" | "attention";
  enabled: boolean;
  command?: string | null;
  args: string[];
  endpoint?: string | null;
  env: McpServerEnvVar[];
  created_at: string;
  updated_at: string;
};

export type ModelProviderTestResult = {
  provider_id: string;
  ok: boolean;
  message: string;
  response_text?: string | null;
  capabilities: Record<string, boolean>;
};

export type TavilySettings = {
  api_key?: string | null;
  enabled: boolean;
};

export type ReviewRequest = {
  playbook_id: string;
  proposal: string;
  mode: "quick" | "standard" | "strict";
  model_provider_id?: string | null;
};

export type CodeReviewChangedFile = {
  path: string;
  old_path?: string | null;
  status: "added" | "modified" | "deleted" | "renamed" | "copied" | "unknown";
  additions: number;
  deletions: number;
  patch: string;
  language?: string | null;
};

export type CodeReviewRequest = {
  playbook_id: string;
  project_id?: string | null;
  agent_id?: string | null;
  mode?: "quick" | "standard" | "strict";
  model_provider_id?: string | null;
  base_ref?: string | null;
  head_ref?: string | null;
  diff_text?: string | null;
  changed_files?: CodeReviewChangedFile[];
  focus?: string[];
  reviewer_note?: string | null;
};

export type ReviewResponse = {
  id: string;
  playbook_id: string;
  mode: "quick" | "standard" | "strict";
  input: string;
  execution_mode: "deterministic" | "llm";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
  overall_judgement: "通过" | "有条件通过" | "建议修改后再评审" | "不建议采用";
  key_risks: string[];
  playbook_conflicts: string[];
  suggested_changes: string[];
  required_validation: string[];
  missing_information: string[];
  findings: Array<{
    severity: "blocker" | "major" | "minor" | "nit";
    confidence: number;
    evidence_level: "confirmed" | "inferred" | "preference" | "unknown";
    rule_id?: string | null;
    problem: string;
    impact: string;
    suggested_change: string;
    required_validation: string[];
    evidence_ids: string[];
  }>;
  model_provider?: string | null;
  created_at: string;
};

export type CodeReviewFileFinding = {
  file_path: string;
  severity: "blocker" | "major" | "minor" | "nit";
  category: "security" | "correctness" | "testing" | "maintainability" | "performance" | "observability";
  title: string;
  detail: string;
  suggestion: string;
  line?: number | null;
  confidence: number;
};

export type CodeReviewResponse = {
  id: string;
  review: ReviewResponse;
  changed_files: CodeReviewChangedFile[];
  file_findings: CodeReviewFileFinding[];
  summary_markdown: string;
  total_files: number;
  total_additions: number;
  total_deletions: number;
  created_at: string;
};

export type CodeReviewChangeListResponse = {
  project_id: string;
  root_path: string;
  base_ref?: string | null;
  head_ref?: string | null;
  changed_files: CodeReviewChangedFile[];
  total_files: number;
  total_additions: number;
  total_deletions: number;
};

export type CodeReviewBranchListResponse = {
  project_id: string;
  root_path: string;
  current_branch?: string | null;
  branches: string[];
};

export type CodeReviewProjectFile = {
  path: string;
  name: string;
  directory: string;
  language?: string | null;
  size_bytes: number;
  updated_at: string;
};

export type CodeReviewProjectFileListResponse = {
  project_id: string;
  root_path: string;
  files: CodeReviewProjectFile[];
  total_files: number;
  truncated: boolean;
};

export type CodeReviewFileDiffResponse = {
  project_id: string;
  root_path: string;
  path: string;
  base_ref?: string | null;
  head_ref?: string | null;
  status: CodeReviewChangedFile["status"];
  additions: number;
  deletions: number;
  patch: string;
  language?: string | null;
  content: string;
  content_truncated: boolean;
};

export type ReviewChatMessage = {
  id: string;
  role: "system" | "user" | "assistant" | "tool" | "llm";
  content: string;
  runtime_id?: string | null;
  call_status?: "running" | "success" | "error" | null;
  provider_id?: string | null;
  model_name?: string | null;
  tool_name?: string | null;
  tool_call_id?: string | null;
  tool_arguments?: string | null;
  tool_result?: string | null;
  created_at: string;
};

export type ReviewSessionContextUsageBreakdown = {
  messages_tokens: number;
  system_prompt_tokens: number;
  playbook_tokens: number;
};

export type ReviewSessionContextUsage = {
  model_name?: string | null;
  provider_name?: string | null;
  context_window: number;
  used_tokens: number;
  remaining_tokens: number;
  usage_percent: number;
  breakdown: ReviewSessionContextUsageBreakdown;
  updated_at: string;
};

export type ReviewConversationSession = {
  id: string;
  playbook_id: string;
  project_id?: string | null;
  agent_id?: string | null;
  mode: "quick" | "standard" | "strict";
  status: "idle" | "running";
  resume_available: boolean;
  resume_reason?: "tool_approval" | "runtime_error" | "cancelled_by_user" | null;
  execution_mode: "deterministic" | "llm";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
  latest_summary?: string | null;
  last_review?: ReviewResponse | null;
  context_usage?: ReviewSessionContextUsage | null;
  messages: ReviewChatMessage[];
  created_at: string;
  updated_at: string;
};

export type ReviewSessionEvent = {
  session_id: string;
  sequence: number;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type ReviewReportAssistantResponse = {
  reply: string;
  suggested_markdown: string;
  execution_mode: "deterministic" | "llm";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
};

export type SkillListItem = {
  name: string;
  description: string;
};

export type ManagedSkillSummary = {
  name: string;
  description: string;
  enabled: boolean;
  source: "builtin" | "uploaded";
  installed_at?: string | null;
  path: string;
};

export type ManagedSkillDetail = ManagedSkillSummary & {
  content: string;
};

export type GraphCapabilityDefinition = {
  id: string;
  name: string;
  kind: "tool" | "skill" | "agent" | "service";
  action: string;
  description: string;
  config: Record<string, unknown>;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  retry_policy: {
    max_attempts: number;
    backoff_seconds: number;
    retry_on: string[];
  };
  enabled: boolean;
  source?: {
    source_type: "skill" | "agent" | "tool" | "mcp_server";
    source_id: string;
    source_name: string;
    metadata: Record<string, unknown>;
  } | null;
  created_at: string;
};

export type GraphCapabilitySourceDescriptor = {
  source_type: "skill" | "agent" | "tool" | "mcp_server";
  source_id: string;
  name: string;
  description: string;
  suggested_kind: "tool" | "skill" | "agent" | "service";
  metadata: Record<string, unknown>;
};

export type GraphCapabilityDraftRequest = {
  kind: "tool" | "skill" | "agent" | "service";
  name: string;
  description: string;
  provider_id?: string | null;
  source_type?: "skill" | "agent" | "tool" | "mcp_server" | null;
  source_id?: string | null;
};

export type GraphCapabilityDraftResponse = {
  capability: GraphCapabilityDefinition;
  execution_mode: "deterministic" | "llm";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
};

export type GraphCompositeNodeDefinition = {
  id: string;
  capability_id: string;
  order: number;
  input_mapping: Record<string, unknown>;
};

export type GraphCompositeDefinition = {
  id: string;
  name: string;
  mode: "chain";
  description: string;
  nodes: GraphCompositeNodeDefinition[];
  created_at: string;
};

export type GraphNodeDefinition = {
  id: string;
  type: "composite" | "capability" | "human_approval";
  capability_id?: string | null;
  composite_id?: string | null;
  approval_label?: string | null;
  config: Record<string, unknown>;
};

export type GraphEdgeDefinition = {
  source: string;
  target: string;
  condition?: string | null;
};

export type GraphPlaybookDefinition = {
  id: string;
  name: string;
  version: string;
  description: string;
  entry_node_id: string;
  nodes: GraphNodeDefinition[];
  edges: GraphEdgeDefinition[];
  created_at: string;
};

export type GraphCompileResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  normalized_definition?: GraphPlaybookDefinition | null;
};

export type GraphRunNodeState = {
  node_id: string;
  status: "pending" | "running" | "waiting_for_human" | "succeeded" | "failed" | "skipped";
  attempts: number;
  started_at?: string | null;
  finished_at?: string | null;
  output: Record<string, unknown>;
  error?: string | null;
};

export type GraphApprovalDecision = {
  approval_id: string;
  node_id: string;
  status: "pending" | "approved" | "rejected";
  decided_by?: string | null;
  decided_at?: string | null;
  comment?: string | null;
};

export type GraphRun = {
  id: string;
  graph_playbook_id: string;
  status: "pending" | "running" | "waiting_for_human" | "succeeded" | "failed" | "cancelled";
  node_states: GraphRunNodeState[];
  approvals: GraphApprovalDecision[];
  current_node_id?: string | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type GraphRunEvent = {
  run_id: string;
  sequence: number;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type KnowledgeWorkspaceSettings = {
  default_root_path?: string | null;
};

export type KnowledgeWorkspaceBinding = {
  project_id?: string | null;
  default_root_path?: string | null;
  project_root_path?: string | null;
  effective_root_path?: string | null;
  scope: "global" | "project" | "unconfigured";
  exists: boolean;
};

export type KnowledgeWorkspaceItem = {
  name: string;
  relative_path: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  updated_at: string;
};

export type KnowledgeWorkspaceListing = {
  root_path?: string | null;
  query: string;
  items: KnowledgeWorkspaceItem[];
  total_items: number;
};

export type KnowledgeWorkspaceUploadResult = {
  root_path: string;
  uploaded_files: string[];
};

export type KnowledgeWorkspaceFileContent = {
  root_path: string;
  relative_path: string;
  content: string;
  truncated: boolean;
  content_type?: "text" | "docx";
};

export type ObservabilitySessionSummary = {
  session_id: string;
  playbook_id?: string | null;
  status?: string | null;
  provider_id?: string | null;
  model_name?: string | null;
  evaluation_grade?: "success" | "partial_success" | "failed" | null;
  anomaly_count: number;
  last_updated_at?: string | null;
  metrics: {
    llm_turn_count: number;
    tool_call_count: number;
    tool_error_count: number;
    tool_error_rate: number;
    session_duration_ms: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    estimated_total_tokens: number;
    max_context_usage_percent: number;
    resume_count: number;
    avg_model_duration_ms: number;
    p95_model_duration_ms: number;
    avg_tool_duration_ms: number;
    slowest_tool_call?: string | null;
  };
};

export type ObservabilityTimelineEntry = {
  event_id: string;
  sequence: number;
  event_type: string;
  timestamp: string;
  title: string;
  summary: string;
  status: "running" | "success" | "error" | "info";
  payload: Record<string, unknown>;
};

export type ObservabilityTaskRecord = {
  task_id: string;
  session_id: string;
  parent_task_id?: string | null;
  source_event_id?: string | null;
  title: string;
  kind: "session" | "llm_turn" | "tool_call" | "delegated_agent";
  status: "pending" | "planning" | "running" | "waiting_child" | "succeeded" | "failed" | "cancelled";
  created_at: string;
  updated_at: string;
  summary?: string | null;
};

export type ObservabilityMetrics = {
  llm_turn_count: number;
  tool_call_count: number;
  tool_error_count: number;
  tool_error_rate: number;
  session_duration_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  estimated_total_tokens: number;
  max_context_usage_percent: number;
  resume_count: number;
  avg_model_duration_ms: number;
  p95_model_duration_ms: number;
  avg_tool_duration_ms: number;
  slowest_tool_call?: string | null;
};

export type ObservabilityEventRecord = {
  event_id: string;
  session_id: string;
  sequence: number;
  event_type: string;
  timestamp: string;
  trace_id?: string | null;
  span_id?: string | null;
  parent_span_id?: string | null;
  runtime_id?: string | null;
  turn?: number | null;
  payload: Record<string, unknown>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      throw new Error(body.detail ?? fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(fallback);
    }
  }

  return (await response.json()) as T;
}

export function scanProject(input: { root_path: string; extra_ignore_patterns: string[] }) {
  return request<ProjectScanSummary>("/projects/scan", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function createProject(input: {
  root_path: string;
  extra_ignore_patterns: string[];
  name?: string;
}) {
  return request<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function deleteProject(projectId: string) {
  return request<{ status: string; project_id: string }>(`/projects/${projectId}`, {
    method: "DELETE"
  });
}

export function listProjects() {
  return request<Project[]>("/projects");
}

export function distillPlaybook(input: { project_id: string; model_provider_id?: string | null }) {
  return request<PlaybookMetadata>("/playbooks/distill", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listPlaybooks() {
  return request<PlaybookMetadata[]>("/playbooks");
}

export function getPlaybook(playbookId: string) {
  return request<PlaybookDetail>(`/playbooks/${playbookId}`);
}

export function createModelProvider(input: ModelProviderConfig) {
  return request<ModelProviderConfig>("/model-providers", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listBusinessAgents() {
  return request<BusinessAgentConfig[]>("/agent-configs");
}

export function createBusinessAgent(input: BusinessAgentConfig) {
  return request<BusinessAgentConfig>("/agent-configs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateBusinessAgent(agentId: string, input: BusinessAgentConfig) {
  return request<BusinessAgentConfig>(`/agent-configs/${agentId}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function activateBusinessAgent(agentId: string) {
  return request<BusinessAgentConfig>(`/agent-configs/${agentId}/activate`, {
    method: "POST",
    body: JSON.stringify({ id: agentId })
  });
}

export function listModelProviders() {
  return request<ModelProviderConfig[]>("/model-providers");
}

export function testProvider(providerId: string) {
  return request<ModelProviderTestResult>(`/model-providers/${providerId}/test`, {
    method: "POST"
  });
}

export function createReview(input: ReviewRequest) {
  return request<ReviewResponse>("/reviews", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listCodeReviewChanges(input: {
  project_id: string;
  base_ref?: string | null;
  head_ref?: string | null;
  paths?: string[];
  include_patch?: boolean;
}) {
  return request<CodeReviewChangeListResponse>("/reviews/code/changes", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listCodeReviewBranches(input: { project_id: string }) {
  return request<CodeReviewBranchListResponse>("/reviews/code/branches", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listCodeReviewProjectFiles(input: {
  project_id: string;
  query?: string | null;
  limit?: number;
}) {
  return request<CodeReviewProjectFileListResponse>("/reviews/code/files", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function getCodeReviewFileDiff(input: {
  project_id: string;
  path: string;
  base_ref?: string | null;
  head_ref?: string | null;
  include_content?: boolean;
}) {
  return request<CodeReviewFileDiffResponse>("/reviews/code/file-diff", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function createCodeReview(input: CodeReviewRequest) {
  return request<CodeReviewResponse>("/reviews/code", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function createReviewSession(input: {
  playbook_id: string;
  project_id?: string | null;
  agent_id?: string | null;
  mode: "quick" | "standard" | "strict";
  model_provider_id?: string | null;
  opening_message?: string | null;
}) {
  return request<ReviewConversationSession>("/reviews/sessions", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function getReviewSession(sessionId: string) {
  return request<ReviewConversationSession>(`/reviews/sessions/${sessionId}`);
}

export function getPlaybookById(playbookId: string) {
  return request<PlaybookDetail>(`/playbooks/${playbookId}`);
}

export function getReviewSessionEventsUrl(sessionId: string) {
  return `${API_BASE}/reviews/sessions/${sessionId}/events`;
}

export function sendReviewMessage(sessionId: string, input: { message: string }, signal?: AbortSignal) {
  return request<ReviewConversationSession>(`/reviews/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify(input),
    signal
  });
}

export function stopReviewSession(sessionId: string) {
  return request<ReviewConversationSession>(`/reviews/sessions/${sessionId}/stop`, {
    method: "POST"
  });
}

export function resumeReviewSession(sessionId: string) {
  return request<ReviewConversationSession>(`/reviews/sessions/${sessionId}/resume`, {
    method: "POST"
  });
}

export function generateReviewReport(input: {
  session_id: string;
  playbook_id: string;
  markdown: string;
  instruction: string;
}) {
  return request<ReviewReportAssistantResponse>("/reviews/report-assistant", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listSkills() {
  return request<SkillListItem[]>("/skills");
}

export function listManagedSkills() {
  return request<ManagedSkillSummary[]>("/skills/manage");
}

export function getTavilySettings() {
  return request<TavilySettings>("/settings/tavily");
}

export function updateTavilySettings(input: { api_key?: string | null; enabled: boolean }) {
  return request<TavilySettings>("/settings/tavily", {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function listMcpServers() {
  return request<McpServerConfig[]>("/mcp-servers");
}

export function getMcpServer(serverId: string) {
  return request<McpServerConfig>(`/mcp-servers/${encodeURIComponent(serverId)}`);
}

export function createMcpServer(input: {
  id?: string | null;
  name: string;
  description: string;
  transport: "stdio" | "streamable_http" | "sse";
  scope: "global" | "project";
  enabled: boolean;
  command?: string | null;
  args: string[];
  endpoint?: string | null;
  env: McpServerEnvVar[];
}) {
  return request<McpServerConfig>("/mcp-servers", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function toggleMcpServer(serverId: string, enabled: boolean) {
  return request<McpServerConfig>(`/mcp-servers/${encodeURIComponent(serverId)}/toggle`, {
    method: "POST",
    body: JSON.stringify({ enabled })
  });
}

export function getManagedSkill(name: string) {
  return request<ManagedSkillDetail>(`/skills/manage/${encodeURIComponent(name)}`);
}

export function listGraphCapabilities() {
  return request<GraphCapabilityDefinition[]>("/graph/capabilities");
}

export function listGraphCapabilitySources() {
  return request<GraphCapabilitySourceDescriptor[]>("/graph/capability-sources");
}

export function getGraphCapability(capabilityId: string) {
  return request<GraphCapabilityDefinition>(`/graph/capabilities/${encodeURIComponent(capabilityId)}`);
}

export function createGraphCapability(input: GraphCapabilityDefinition) {
  return request<GraphCapabilityDefinition>("/graph/capabilities", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateGraphCapability(capabilityId: string, input: GraphCapabilityDefinition) {
  return request<GraphCapabilityDefinition>(`/graph/capabilities/${encodeURIComponent(capabilityId)}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function deleteGraphCapability(capabilityId: string) {
  return request<{ status: string; capability_id: string }>(`/graph/capabilities/${encodeURIComponent(capabilityId)}`, {
    method: "DELETE"
  });
}

export function draftGraphCapability(input: GraphCapabilityDraftRequest) {
  return request<GraphCapabilityDraftResponse>("/graph/capabilities/draft", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function listGraphComposites() {
  return request<GraphCompositeDefinition[]>("/graph/composites");
}

export function getGraphComposite(compositeId: string) {
  return request<GraphCompositeDefinition>(`/graph/composites/${encodeURIComponent(compositeId)}`);
}

export function createGraphComposite(input: GraphCompositeDefinition) {
  return request<GraphCompositeDefinition>("/graph/composites", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateGraphComposite(compositeId: string, input: GraphCompositeDefinition) {
  return request<GraphCompositeDefinition>(`/graph/composites/${encodeURIComponent(compositeId)}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function deleteGraphComposite(compositeId: string) {
  return request<{ status: string; composite_id: string }>(`/graph/composites/${encodeURIComponent(compositeId)}`, {
    method: "DELETE"
  });
}

export function compileGraphComposite(compositeId: string) {
  return request<GraphCompileResult>(`/graph/composites/${encodeURIComponent(compositeId)}/compile`, {
    method: "POST"
  });
}

export function listGraphPlaybooks() {
  return request<GraphPlaybookDefinition[]>("/graph/playbooks");
}

export function getGraphPlaybook(playbookId: string) {
  return request<GraphPlaybookDefinition>(`/graph/playbooks/${encodeURIComponent(playbookId)}`);
}

export function createGraphPlaybook(input: GraphPlaybookDefinition) {
  return request<GraphPlaybookDefinition>("/graph/playbooks", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function updateGraphPlaybook(playbookId: string, input: GraphPlaybookDefinition) {
  return request<GraphPlaybookDefinition>(`/graph/playbooks/${encodeURIComponent(playbookId)}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function deleteGraphPlaybook(playbookId: string) {
  return request<{ status: string; graph_playbook_id: string }>(`/graph/playbooks/${encodeURIComponent(playbookId)}`, {
    method: "DELETE"
  });
}

export function compileGraphPlaybook(playbookId: string) {
  return request<GraphCompileResult>(`/graph/playbooks/${encodeURIComponent(playbookId)}/compile`, {
    method: "POST"
  });
}

export function listGraphRuns() {
  return request<GraphRun[]>("/graph/runs");
}

export function createGraphRun(playbookId: string, input: { input_payload: Record<string, unknown> }) {
  return request<GraphRun>(`/graph/playbooks/${encodeURIComponent(playbookId)}/runs`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function getGraphRun(runId: string) {
  return request<GraphRun>(`/graph/runs/${encodeURIComponent(runId)}`);
}

export function submitGraphApproval(
  runId: string,
  approvalId: string,
  input: { approved: boolean; decided_by: string; comment?: string | null }
) {
  return request<GraphRun>(`/graph/runs/${encodeURIComponent(runId)}/approvals/${encodeURIComponent(approvalId)}`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function getGraphRunEventsUrl(runId: string) {
  return `${API_BASE}/graph/runs/${encodeURIComponent(runId)}/events`;
}

export function toggleManagedSkill(name: string, enabled: boolean) {
  return request<ManagedSkillDetail>(`/skills/manage/${encodeURIComponent(name)}/toggle`, {
    method: "POST",
    body: JSON.stringify({ enabled })
  });
}

export function deleteManagedSkill(name: string) {
  return request<{ status: string; name: string }>(`/skills/manage/${encodeURIComponent(name)}`, {
    method: "DELETE"
  });
}

export async function uploadSkillZip(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/skills/manage/upload`, {
    method: "POST",
    body: formData,
    cache: "no-store"
  });
  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      throw new Error(body.detail ?? fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(fallback);
    }
  }
  return (await response.json()) as { installed: ManagedSkillDetail };
}

export function getKnowledgeWorkspaceSettings() {
  return request<KnowledgeWorkspaceSettings>("/knowledge-workspace");
}

export function updateKnowledgeWorkspaceSettings(input: { root_path?: string | null }) {
  return request<KnowledgeWorkspaceSettings>("/knowledge-workspace", {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function pickKnowledgeWorkspaceFolder() {
  return request<{ path: string }>("/knowledge-workspace/pick-folder", {
    method: "POST"
  });
}

export function getKnowledgeWorkspaceBinding(projectId?: string | null) {
  const params = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<KnowledgeWorkspaceBinding>(`/knowledge-workspace/binding${params}`);
}

export function getProjectKnowledgeWorkspace(projectId: string) {
  return request<KnowledgeWorkspaceBinding>(`/knowledge-workspace/projects/${projectId}`);
}

export function updateProjectKnowledgeWorkspace(projectId: string, input: { root_path?: string | null }) {
  return request<KnowledgeWorkspaceBinding>(`/knowledge-workspace/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export function listKnowledgeWorkspaceFiles(input?: { project_id?: string | null; query?: string }) {
  const search = new URLSearchParams();
  if (input?.project_id) {
    search.set("project_id", input.project_id);
  }
  if (input?.query) {
    search.set("query", input.query);
  }
  const suffix = search.size ? `?${search.toString()}` : "";
  return request<KnowledgeWorkspaceListing>(`/knowledge-workspace/files${suffix}`);
}

export async function uploadKnowledgeWorkspaceFiles(input: { project_id?: string | null; files: File[] }) {
  const search = new URLSearchParams();
  if (input.project_id) {
    search.set("project_id", input.project_id);
  }
  const suffix = search.size ? `?${search.toString()}` : "";
  const formData = new FormData();
  for (const file of input.files) {
    formData.append("files", file);
  }
  const response = await fetch(`${API_BASE}/knowledge-workspace/files/upload${suffix}`, {
    method: "POST",
    body: formData,
    cache: "no-store"
  });
  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      throw new Error(body.detail ?? fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
      throw new Error(fallback);
    }
  }
  return (await response.json()) as KnowledgeWorkspaceUploadResult;
}

export function saveKnowledgeWorkspaceMarkdown(input: { project_id?: string | null; filename: string; content: string }) {
  return request<KnowledgeWorkspaceUploadResult>("/knowledge-workspace/files/save-text", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function saveKnowledgeWorkspaceDocx(input: {
  project_id?: string | null;
  filename: string;
  content: string;
  source_relative_path?: string | null;
}) {
  return request<KnowledgeWorkspaceUploadResult>("/knowledge-workspace/files/save-docx", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export function getKnowledgeWorkspaceFileContent(input: { project_id?: string | null; relative_path: string }) {
  const search = new URLSearchParams();
  if (input.project_id) {
    search.set("project_id", input.project_id);
  }
  search.set("relative_path", input.relative_path);
  return request<KnowledgeWorkspaceFileContent>(`/knowledge-workspace/files/content?${search.toString()}`);
}

export function getKnowledgeWorkspaceDocxContent(input: { project_id?: string | null; relative_path: string }) {
  const search = new URLSearchParams();
  if (input.project_id) {
    search.set("project_id", input.project_id);
  }
  search.set("relative_path", input.relative_path);
  return request<KnowledgeWorkspaceFileContent>(`/knowledge-workspace/files/docx/content?${search.toString()}`);
}

export function listObservabilitySessions() {
  return request<ObservabilitySessionSummary[]>("/observability/sessions");
}

export function getObservabilityTimeline(sessionId: string) {
  return request<ObservabilityTimelineEntry[]>(`/observability/sessions/${encodeURIComponent(sessionId)}/timeline`);
}

export function getObservabilityTasks(sessionId: string) {
  return request<ObservabilityTaskRecord[]>(`/observability/sessions/${encodeURIComponent(sessionId)}/tasks`);
}

export function getObservabilityMetrics(sessionId: string) {
  return request<ObservabilityMetrics>(`/observability/sessions/${encodeURIComponent(sessionId)}/metrics`);
}

export function getObservabilitySessionDetail(sessionId: string) {
  return request<ObservabilitySessionSummary>(`/observability/sessions/${encodeURIComponent(sessionId)}`);
}

export function getObservabilityEvents(sessionId: string) {
  return request<ObservabilityEventRecord[]>(`/observability/sessions/${encodeURIComponent(sessionId)}/events`);
}
