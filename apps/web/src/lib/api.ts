export type Project = {
  id: string;
  name: string;
  root_path: string;
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

export type ModelProviderTestResult = {
  provider_id: string;
  ok: boolean;
  message: string;
  response_text?: string | null;
  capabilities: Record<string, boolean>;
};

export type ReviewRequest = {
  playbook_id: string;
  proposal: string;
  mode: "quick" | "standard" | "strict";
  model_provider_id?: string | null;
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

export type ReviewChatMessage = {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  created_at: string;
};

export type ReviewConversationSession = {
  id: string;
  playbook_id: string;
  project_id?: string | null;
  mode: "quick" | "standard" | "strict";
  status: "idle" | "running";
  resume_available: boolean;
  resume_reason?: "interruption" | "error" | "cancelled" | null;
  execution_mode: "deterministic" | "llm";
  resolved_provider_id?: string | null;
  execution_note?: string | null;
  latest_summary?: string | null;
  last_review?: ReviewResponse | null;
  messages: ReviewChatMessage[];
  created_at: string;
  updated_at: string;
};

export type SkillListItem = {
  name: string;
  description: string;
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

export function createReviewSession(input: {
  playbook_id: string;
  project_id?: string | null;
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

export function listSkills() {
  return request<SkillListItem[]>("/skills");
}
