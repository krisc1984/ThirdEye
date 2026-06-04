"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import { MarkdownMessage } from "@/components/MarkdownMessage";

import type {
  KnowledgeWorkspaceBinding,
  KnowledgeWorkspaceListing,
  ModelProviderConfig,
  PlaybookDetail,
  PlaybookMetadata,
  Project,
  ReviewConversationSession,
  ReviewSessionEvent,
  ReviewResponse,
  SkillListItem
} from "@/lib/api";
import {
  createProject,
  createReviewSession,
  deleteProject,
  getPlaybook,
  getKnowledgeWorkspaceBinding,
  getReviewSession,
  getReviewSessionEventsUrl,
  listKnowledgeWorkspaceFiles,
  pickKnowledgeWorkspaceFolder,
  resumeReviewSession,
  sendReviewMessage,
  stopReviewSession
  ,
  updateKnowledgeWorkspaceSettings,
  updateProjectKnowledgeWorkspace,
  uploadKnowledgeWorkspaceFiles
} from "@/lib/api";

type AgentWorkspaceProps = {
  playbooks: PlaybookMetadata[];
  modelProviders: ModelProviderConfig[];
  projects: Project[];
  skills: SkillListItem[];
  activeAgentName?: string | null;
};

type WorkspaceMessage = {
  id: string;
  role: "user" | "assistant" | "tool" | "llm";
  content: string;
  timestamp: string;
  runtimeId?: string | null;
  callStatus?: "running" | "success" | "error" | null;
  providerId?: string | null;
  modelName?: string | null;
  toolName?: string | null;
  toolCallId?: string | null;
  toolArguments?: string | null;
  toolResult?: string | null;
};

type KnowledgeItem = {
  id: string;
  name: string;
  kind: "pdf" | "doc" | "uml" | "sheet" | "folder";
  size: string;
  updatedAt: string;
  folder: string;
};

type KnowledgeTreeNode = {
  id: string;
  name: string;
  path: string;
  kind: KnowledgeItem["kind"];
  size?: string;
  updatedAt?: string;
  isDir: boolean;
  children: KnowledgeTreeNode[];
};

const capabilityCards = [
  {
    title: "结构眼",
    tone: "blue",
    description: "看架构合理性与设计完备性"
  },
  {
    title: "风险眼",
    tone: "orange",
    description: "识别风险隐患与影响范围"
  },
  {
    title: "实现眼",
    tone: "green",
    description: "评估可落地性与最佳实践"
  }
] as const;

const starterPrompts = [
  "请评审一下订单中心的重构方案，重点关注并发场景下的数据一致性。",
  "帮我分析这个方案的高风险点，并给出修改建议和验证路径。",
  "从结构、风险、实现三个角度分别给出结论。"
];

const fallbackKnowledgeItems: KnowledgeItem[] = [
  {
    id: "sample-1",
    name: "01_架构设计说明.pdf",
    kind: "pdf",
    size: "2.4 MB",
    updatedAt: "05-20",
    folder: "订单中心重构方案"
  },
  {
    id: "sample-2",
    name: "02_接口说明.md",
    kind: "doc",
    size: "1.1 MB",
    updatedAt: "05-20",
    folder: "订单中心重构方案"
  },
  {
    id: "sample-3",
    name: "03_时序图.puml",
    kind: "uml",
    size: "860 KB",
    updatedAt: "05-19",
    folder: "订单中心重构方案"
  },
  {
    id: "sample-4",
    name: "04_数据模型设计.xlsx",
    kind: "sheet",
    size: "320 KB",
    updatedAt: "05-19",
    folder: "订单中心重构方案"
  }
];

const formatTime = (value: string) =>
  new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));

const formatBytes = (value: number) => {
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  if (value >= 1024) return `${Math.round(value / 1024)} KB`;
  return `${value} B`;
};

const formatInteger = (value: number) => new Intl.NumberFormat("en-US").format(value);

const kindLabel: Record<KnowledgeItem["kind"], string> = {
  folder: "目录",
  pdf: "PDF",
  doc: "文档",
  uml: "图表",
  sheet: "表格"
};

function summariseReview(review: ReviewResponse | null) {
  if (!review) {
    return {
      overview: "请选择项目空间并发起一次对话，右侧会在多轮会话过程中持续沉淀结构、风险与实现结论。",
      riskCounts: { blocker: 0, major: 0, minor: 0 },
      recommendations: [
        "优先确认关键链路与业务边界",
        "补充约束条件、性能目标和回滚策略",
        "将验证计划写进对话，便于 agent 连续跟进"
      ]
    };
  }

  const riskCounts = review.findings.reduce(
    (acc, finding) => {
      if (finding.severity === "blocker") acc.blocker += 1;
      if (finding.severity === "major") acc.major += 1;
      if (finding.severity === "minor") acc.minor += 1;
      return acc;
    },
    { blocker: 0, major: 0, minor: 0 }
  );

  return {
    overview: review.key_risks[0] ?? review.suggested_changes[0] ?? review.overall_judgement,
    riskCounts,
    recommendations:
      review.suggested_changes.slice(0, 3).length > 0
        ? review.suggested_changes.slice(0, 3)
        : review.required_validation.slice(0, 3)
  };
}

function iconForKind(kind: KnowledgeItem["kind"]) {
  switch (kind) {
    case "folder":
      return "▾";
    case "pdf":
      return "PDF";
    case "doc":
      return "MD";
    case "uml":
      return "UML";
    case "sheet":
      return "XLS";
    default:
      return "文件";
  }
}

const resumeReasonLabel: Record<NonNullable<ReviewConversationSession["resume_reason"]>, string> = {
  tool_approval: "工具执行被中断，可从断点继续",
  runtime_error: "运行异常后已保存断点，可继续尝试",
  cancelled_by_user: "你已终止本次执行，可从断点继续"
};

function statusIcon(status?: "running" | "success" | "error" | null) {
  if (status === "success") return "✓";
  if (status === "error") return "✕";
  return "…";
}

function buildKnowledgeTree(items: KnowledgeItem[]): KnowledgeTreeNode[] {
  const root: KnowledgeTreeNode = {
    id: "__root__",
    name: "root",
    path: "",
    kind: "folder",
    isDir: true,
    children: []
  };
  const nodeMap = new Map<string, KnowledgeTreeNode>([[root.id, root]]);

  const ensureDirNode = (dirPath: string) => {
    if (!dirPath) {
      return root;
    }
    const existing = nodeMap.get(dirPath);
    if (existing) {
      return existing;
    }
    const segments = dirPath.split("/").filter(Boolean);
    const parentPath = segments.slice(0, -1).join("/");
    const parent = ensureDirNode(parentPath);
    const node: KnowledgeTreeNode = {
      id: dirPath,
      name: segments[segments.length - 1],
      path: dirPath,
      kind: "folder",
      isDir: true,
      children: []
    };
    parent.children.push(node);
    nodeMap.set(dirPath, node);
    return node;
  };

  for (const item of items) {
    const relativePath = item.folder === "根目录" ? item.name : `${item.folder}/${item.name}`;
    const normalizedPath = relativePath.replace(/^\/+/, "");
    const parentPath =
      item.kind === "folder"
        ? normalizedPath.split("/").slice(0, -1).join("/")
        : normalizedPath.split("/").slice(0, -1).join("/");
    const parent = ensureDirNode(parentPath);

    if (item.kind === "folder") {
      ensureDirNode(normalizedPath);
      continue;
    }

    parent.children.push({
      id: normalizedPath,
      name: item.name,
      path: normalizedPath,
      kind: item.kind,
      size: item.size,
      updatedAt: item.updatedAt,
      isDir: false,
      children: []
    });
  }

  const sortNodes = (nodes: KnowledgeTreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isDir !== b.isDir) {
        return a.isDir ? -1 : 1;
      }
      return a.name.localeCompare(b.name, "zh-CN");
    });
    for (const node of nodes) {
      if (node.children.length) {
        sortNodes(node.children);
      }
    }
  };

  sortNodes(root.children);
  return root.children;
}

export function AgentWorkspace({ playbooks, modelProviders, projects, skills, activeAgentName }: AgentWorkspaceProps) {
  const [workspaceProjects, setWorkspaceProjects] = useState<Project[]>(
    () => projects.filter((project) => project.name !== "Sample Project")
  );
  const [selectedPlaybookId, setSelectedPlaybookId] = useState(playbooks[0]?.id ?? "");
  const [selectedProjectId, setSelectedProjectId] = useState(
    () => projects.find((project) => project.name !== "Sample Project")?.id ?? ""
  );
  const [selectedModelProviderId, setSelectedModelProviderId] = useState(modelProviders[0]?.id ?? "");
  const [mode, setMode] = useState<"quick" | "standard" | "strict">("standard");
  const [draft, setDraft] = useState("");
  const [lastSubmittedDraft, setLastSubmittedDraft] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectPath, setNewProjectPath] = useState("");
  const [showProjectCreator, setShowProjectCreator] = useState(false);
  const [selectedSkillName, setSelectedSkillName] = useState("");
  const [knowledgeBinding, setKnowledgeBinding] = useState<KnowledgeWorkspaceBinding | null>(null);
  const [knowledgeListing, setKnowledgeListing] = useState<KnowledgeWorkspaceListing | null>(null);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [isKnowledgeLoading, setIsKnowledgeLoading] = useState(false);
  const [knowledgeUploadInputKey, setKnowledgeUploadInputKey] = useState(0);
  const [expandedKnowledgePaths, setExpandedKnowledgePaths] = useState<Record<string, boolean>>({});
  const [session, setSession] = useState<ReviewConversationSession | null>(null);
  const [sessionHistory, setSessionHistory] = useState<ReviewConversationSession[]>([]);
  const [playbookDetail, setPlaybookDetail] = useState<PlaybookDetail | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isPending, startTransition] = useTransition();
  const requestAbortRef = useRef<AbortController | null>(null);
  const chatRef = useRef<HTMLDivElement | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const knowledgeUploadInputRef = useRef<HTMLInputElement | null>(null);
  const draftTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setSelectedPlaybookId((current) => current || playbooks[0]?.id || "");
  }, [playbooks]);

  useEffect(() => {
    setWorkspaceProjects(projects.filter((project) => project.name !== "Sample Project"));
  }, [projects]);

  useEffect(() => {
    setSelectedProjectId((current) => {
      if (current && workspaceProjects.some((project) => project.id === current)) {
        return current;
      }
      return workspaceProjects[0]?.id ?? "";
    });
  }, [workspaceProjects]);

  useEffect(() => {
    if (!session) {
      return;
    }
    setSessionHistory((current) => {
      const next = [session, ...current.filter((item) => item.id !== session.id)];
      return next.slice(0, 6);
    });
  }, [session]);

  const selectedProject = useMemo(
    () => workspaceProjects.find((project) => project.id === selectedProjectId) ?? workspaceProjects[0] ?? null,
    [workspaceProjects, selectedProjectId]
  );

  const projectScopedPlaybooks = useMemo(() => {
    if (!selectedProject) {
      return playbooks;
    }

    const filtered = playbooks.filter((playbook) => playbook.project_id === selectedProject.id);
    return filtered.length ? filtered : playbooks;
  }, [playbooks, selectedProject]);

  useEffect(() => {
    if (!projectScopedPlaybooks.find((playbook) => playbook.id === selectedPlaybookId)) {
      setSelectedPlaybookId(projectScopedPlaybooks[0]?.id ?? "");
    }
  }, [projectScopedPlaybooks, selectedPlaybookId]);

  useEffect(() => {
    if (!selectedPlaybookId && projectScopedPlaybooks.length > 0) {
      setSelectedPlaybookId(projectScopedPlaybooks[0].id);
    }
  }, [projectScopedPlaybooks, selectedPlaybookId]);

  const mappedMessages: WorkspaceMessage[] = useMemo(() => {
    if (!session) {
      return [];
    }

    return session.messages
      .filter((message) => message.role !== "system")
      .map((message) => ({
        id: message.id,
        role:
          message.role === "assistant"
            ? "assistant"
            : message.role === "llm"
              ? "llm"
            : message.role === "tool"
              ? "tool"
              : "user",
        content: message.content,
        timestamp: formatTime(message.created_at),
        runtimeId: message.runtime_id,
        callStatus: message.call_status,
        providerId: message.provider_id,
        modelName: message.model_name,
        toolName: message.tool_name,
        toolCallId: message.tool_call_id,
        toolArguments: message.tool_arguments,
        toolResult: message.tool_result
      }));
  }, [session]);

  useEffect(() => {
    const chatElement = chatRef.current;
    if (!chatElement) {
      return;
    }
    chatElement.scrollTo({
      top: chatElement.scrollHeight,
      behavior: "smooth"
    });
  }, [mappedMessages]);

  function connectSessionEvents(sessionId: string) {
    eventSourceRef.current?.close();
    const eventSource = new EventSource(getReviewSessionEventsUrl(sessionId));
    eventSourceRef.current = eventSource;

    const applyEvent = (parsed: ReviewSessionEvent) => {
      setSession((current) => {
        if (!current || current.id !== sessionId || current.id !== parsed.session_id) {
          return current;
        }

        if (parsed.event_type === "session.snapshot") {
          return parsed.payload as unknown as ReviewConversationSession;
        }

        const next: ReviewConversationSession = {
          ...current,
          messages: [...current.messages],
        };
        const payload = parsed.payload;

        if (typeof payload.status === "string") {
          next.status = payload.status as ReviewConversationSession["status"];
        }
        if ("execution_note" in payload) {
          next.execution_note = (payload.execution_note as string | null | undefined) ?? null;
        }
        if ("resume_available" in payload) {
          next.resume_available = Boolean(payload.resume_available);
        }
        if ("resume_reason" in payload) {
          next.resume_reason = (payload.resume_reason as ReviewConversationSession["resume_reason"]) ?? null;
        }
        if ("latest_summary" in payload) {
          next.latest_summary = (payload.latest_summary as string | null | undefined) ?? null;
        }
        if ("resolved_provider_id" in payload) {
          next.resolved_provider_id = (payload.resolved_provider_id as string | null | undefined) ?? null;
        }
        if ("execution_mode" in payload) {
          next.execution_mode = payload.execution_mode as ReviewConversationSession["execution_mode"];
        }
        if ("last_review" in payload) {
          next.last_review = (payload.last_review as ReviewResponse | null | undefined) ?? null;
        }
        if (typeof payload.updated_at === "string") {
          next.updated_at = payload.updated_at;
        }

        const eventMessage = payload.message as ReviewConversationSession["messages"][number] | undefined;
        if (eventMessage?.id) {
          const existingIndex = next.messages.findIndex((item) => item.id === eventMessage.id);
          if (existingIndex >= 0) {
            next.messages[existingIndex] = eventMessage;
          } else {
            next.messages.push(eventMessage);
          }
        }

        return next;
      });
    };

    const handleMessage = (event: MessageEvent<string>) => {
      try {
        applyEvent(JSON.parse(event.data) as ReviewSessionEvent);
      } catch {
        // Ignore malformed event payloads.
      }
    };

    eventSource.onmessage = handleMessage;
    for (const eventName of [
      "session.snapshot",
      "session.status",
      "message.user",
      "message.assistant",
      "llm.start",
      "llm.end",
      "tool.start",
      "tool.end",
      "session.resume_available",
      "session.resume_cleared",
      "session.done",
    ]) {
      eventSource.addEventListener(eventName, handleMessage as EventListener);
    }

    eventSource.addEventListener("session.done", () => {
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
    });

    eventSource.onerror = () => {
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
    };

  }

  useEffect(() => {
    if (!session?.id) {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      return;
    }

    connectSessionEvents(session.id);

    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, [session?.id]);

  const evidenceKnowledgeItems = useMemo<KnowledgeItem[]>(() => {
    if (knowledgeListing?.items.length) {
      return knowledgeListing.items.map((item) => ({
        id: item.relative_path,
        name: item.name,
        kind: item.is_dir
          ? "folder"
          : item.name.endsWith(".pdf")
            ? "pdf"
            : item.name.endsWith(".puml") || item.name.endsWith(".uml")
              ? "uml"
              : item.name.endsWith(".xlsx") || item.name.endsWith(".xls") || item.name.endsWith(".csv")
                ? "sheet"
                : "doc",
        size: item.is_dir ? "--" : formatBytes(item.size_bytes),
        updatedAt: formatTime(item.updated_at),
        folder: item.relative_path.includes("/") ? item.relative_path.split("/").slice(0, -1).join("/") : "根目录"
      }));
    }
    if (knowledgeBinding?.effective_root_path) {
      return [];
    }
    const evidence = playbookDetail?.evidence ?? [];
    if (!evidence.length) {
      return fallbackKnowledgeItems;
    }

    return evidence.slice(0, 8).map((item, index) => ({
      id: item.id,
      name: item.path.split(/[\\/]/).pop() || item.path,
      kind: item.source_type === "doc" ? "doc" : item.source_type === "config" ? "sheet" : "pdf",
      size: `${(item.summary.length * 2 + 40).toString()} KB`,
      updatedAt: `0${(index % 9) + 1}-1${index % 9}`,
      folder: item.source_type === "doc" ? "知识库文档" : "评审证据"
    }));
  }, [knowledgeBinding?.effective_root_path, knowledgeListing, playbookDetail]);

  const knowledgeGroups = useMemo(() => {
    const groups = new Map<string, KnowledgeItem[]>();
    for (const item of evidenceKnowledgeItems) {
      const list = groups.get(item.folder) ?? [];
      list.push(item);
      groups.set(item.folder, list);
    }
    return Array.from(groups.entries());
  }, [evidenceKnowledgeItems]);

  const knowledgeTree = useMemo(() => buildKnowledgeTree(evidenceKnowledgeItems), [evidenceKnowledgeItems]);

  const reviewSummary = useMemo(() => summariseReview(session?.last_review ?? null), [session]);

  const selectedPlaybook = useMemo(
    () => playbooks.find((playbook) => playbook.id === selectedPlaybookId) ?? null,
    [playbooks, selectedPlaybookId]
  );
  const selectedModelProvider = useMemo(
    () => modelProviders.find((provider) => provider.id === selectedModelProviderId) ?? null,
    [modelProviders, selectedModelProviderId]
  );
  const contextUsage = useMemo(() => {
    if (!session?.context_usage) {
      return null;
    }
    if (
      session.resolved_provider_id &&
      selectedModelProviderId &&
      session.resolved_provider_id !== selectedModelProviderId
    ) {
      return null;
    }
    return session.context_usage;
  }, [selectedModelProviderId, session]);

  async function refreshKnowledgeWorkspace(projectId = selectedProjectId, query = knowledgeQuery) {
    setIsKnowledgeLoading(true);
    try {
      const [binding, listing] = await Promise.all([
        getKnowledgeWorkspaceBinding(projectId || undefined),
        listKnowledgeWorkspaceFiles({ project_id: projectId || undefined, query })
      ]);
      setKnowledgeBinding(binding);
      setKnowledgeListing(listing);
      setExpandedKnowledgePaths((current) => {
        if (Object.keys(current).length > 0) {
          return current;
        }
        const next: Record<string, boolean> = {};
        for (const item of listing.items) {
          if (item.is_dir) {
            next[item.relative_path] = item.relative_path.split("/").length <= 1;
          }
        }
        return next;
      });
    } catch (caughtError) {
      setKnowledgeBinding(null);
      setKnowledgeListing(null);
      setError(caughtError instanceof Error ? caughtError.message : "加载资料区失败");
    } finally {
      setIsKnowledgeLoading(false);
    }
  }

  useEffect(() => {
    void refreshKnowledgeWorkspace();
  }, [selectedProjectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshKnowledgeWorkspace(selectedProjectId, knowledgeQuery);
    }, 200);
    return () => window.clearTimeout(timer);
  }, [knowledgeQuery]);

  async function ensurePlaybookDetail(playbookId: string) {
    if (playbookDetail?.metadata.id === playbookId) {
      return playbookDetail;
    }

    const loaded = await getPlaybook(playbookId);
    setPlaybookDetail(loaded);
    return loaded;
  }

  async function handlePromptSubmit(message: string) {
    if (!selectedPlaybookId || !message.trim()) {
      return;
    }

    const submittedMessage = message.trim();
    setError(null);
    setIsSending(true);
    const controller = new AbortController();
    requestAbortRef.current = controller;
    try {
      await ensurePlaybookDetail(selectedPlaybookId);
      const targetSession =
        !session || session.playbook_id !== selectedPlaybookId
          ? await createReviewSession({
              playbook_id: selectedPlaybookId,
              project_id: selectedProjectId || undefined,
              mode,
              ...(selectedModelProviderId ? { model_provider_id: selectedModelProviderId } : {})
            })
          : session;
      if (!session || session.playbook_id !== selectedPlaybookId) {
        setSession(targetSession);
      }
      connectSessionEvents(targetSession.id);
      setSession((current) =>
        current && current.id === targetSession.id
          ? { ...current, status: "running" }
          : { ...targetSession, status: "running" }
      );
      const updated = await sendReviewMessage(
        targetSession.id,
        { message: submittedMessage },
        controller.signal
      );
      setSession(updated);
      setLastSubmittedDraft(submittedMessage);
      setDraft("");
    } catch (caughtError) {
      if (caughtError instanceof Error && caughtError.name === "AbortError") {
        setError("已终止当前会话请求");
      } else {
        setError(caughtError instanceof Error ? caughtError.message : "评审会话启动失败");
      }
    } finally {
      if (requestAbortRef.current === controller) {
        requestAbortRef.current = null;
      }
      setIsSending(false);
    }
  }

  async function handleStopSession() {
    const activeSessionId = session?.id;
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (!activeSessionId) {
      setIsSending(false);
      return;
    }

    try {
      const updated = await stopReviewSession(activeSessionId);
      setSession(updated);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "终止会话失败");
    } finally {
      setIsSending(false);
    }
  }

  async function handleResumeSession() {
    if (!session?.id || !session.resume_available) {
      return;
    }

    setError(null);
    setIsSending(true);
    try {
      connectSessionEvents(session.id);
      const updated = await resumeReviewSession(session.id);
      setSession(updated);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "继续执行失败");
    } finally {
      setIsSending(false);
    }
  }

  function handleCreateProject() {
    if (!newProjectName.trim() || !newProjectPath.trim()) {
      setError("请填写项目名称和项目路径");
      return;
    }

    setError(null);
    startTransition(async () => {
      try {
        const created = await createProject({
          name: newProjectName.trim(),
          root_path: newProjectPath.trim(),
          extra_ignore_patterns: []
        });

        if (created.name === "Sample Project") {
          return;
        }

        setWorkspaceProjects((current) => [created, ...current.filter((project) => project.id !== created.id)]);
        setSelectedProjectId(created.id);
        setNewProjectName("");
        setNewProjectPath("");
        setShowProjectCreator(false);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "创建项目失败");
      }
    });
  }

  function handleDeleteProject(projectId: string) {
    setError(null);
    startTransition(async () => {
      try {
        await deleteProject(projectId);
        setWorkspaceProjects((current) => {
          const next = current.filter((project) => project.id !== projectId);
          if (selectedProjectId === projectId) {
            setSelectedProjectId(next[0]?.id ?? "");
            setSession(null);
            setPlaybookDetail(null);
          }
          return next;
        });
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "删除项目失败");
      }
    });
  }

  function handleStartNewConversation() {
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setSession(null);
    setDraft("");
    setLastSubmittedDraft("");
    setError(null);
    setIsSending(false);
  }

  function handleDraftKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "ArrowUp") {
      return;
    }

    const textarea = event.currentTarget;
    const hasSelection =
      textarea.selectionStart !== textarea.selectionEnd;
    const isCursorAtStart = textarea.selectionStart === 0 && textarea.selectionEnd === 0;
    if (!lastSubmittedDraft || draft.trim() || hasSelection || !isCursorAtStart) {
      return;
    }

    event.preventDefault();
    setDraft(lastSubmittedDraft);
    requestAnimationFrame(() => {
      const nextLength = lastSubmittedDraft.length;
      textarea.setSelectionRange(nextLength, nextLength);
    });
  }

  async function handleCopyMessage(messageId: string, content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === messageId ? null : current));
      }, 1800);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "复制失败");
    }
  }

  async function handlePickKnowledgeFolder(scope: "global" | "project") {
    try {
      setError(null);
      const picked = await pickKnowledgeWorkspaceFolder();
      if (scope === "global") {
        await updateKnowledgeWorkspaceSettings({ root_path: picked.path });
      } else if (selectedProjectId) {
        await updateProjectKnowledgeWorkspace(selectedProjectId, { root_path: picked.path });
      }
      await refreshKnowledgeWorkspace();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "选择资料区文件夹失败");
    }
  }

  async function handleClearProjectKnowledgeOverride() {
    if (!selectedProjectId) {
      return;
    }
    try {
      setError(null);
      await updateProjectKnowledgeWorkspace(selectedProjectId, { root_path: null });
      await refreshKnowledgeWorkspace();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "恢复全局资料区失败");
    }
  }

  function handleOpenKnowledgeUploadPicker() {
    if (!knowledgeBinding?.effective_root_path) {
      setError("请先设置资料区，再上传文档。");
      return;
    }
    knowledgeUploadInputRef.current?.click();
  }

  async function handleKnowledgeUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }
    try {
      setError(null);
      const result = await uploadKnowledgeWorkspaceFiles({
        project_id: selectedProjectId || undefined,
        files
      });
      setKnowledgeUploadInputKey((current) => current + 1);
      await refreshKnowledgeWorkspace();
      if (result.uploaded_files.length) {
        const mentionText = result.uploaded_files.map((name) => `@资料/${name}`).join(" ");
        setDraft((current) => (current.trim() ? `${current.trimEnd()}\n${mentionText}` : mentionText));
        requestAnimationFrame(() => {
          const textarea = draftTextareaRef.current;
          if (!textarea) {
            return;
          }
          textarea.focus();
          const nextLength = textarea.value.length;
          textarea.setSelectionRange(nextLength, nextLength);
        });
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "上传资料失败");
    }
  }

  function renderKnowledgeNodes(nodes: KnowledgeTreeNode[], depth = 0): React.ReactNode {
    return nodes.map((node) => {
      if (node.isDir) {
        const expanded = expandedKnowledgePaths[node.path] ?? depth === 0;
        return (
          <div key={node.id} className="workspace-doc-node">
            <button
              type="button"
              className="workspace-doc-node__dir"
              style={{ paddingLeft: `${depth * 16}px` }}
              onClick={() =>
                setExpandedKnowledgePaths((current) => ({
                  ...current,
                  [node.path]: !expanded
                }))
              }
            >
              <span>{expanded ? "▾" : "▸"}</span>
              <strong>{node.name}</strong>
            </button>
            {expanded ? <div className="workspace-doc-node__children">{renderKnowledgeNodes(node.children, depth + 1)}</div> : null}
          </div>
        );
      }

      return (
        <div
          key={node.id}
          className="workspace-doc-item"
          style={{ paddingLeft: `${depth * 16}px` }}
        >
          <span className={`workspace-doc-item__icon workspace-doc-item__icon--${node.kind}`}>
            {iconForKind(node.kind)}
          </span>
          <div className="workspace-doc-item__body">
            <strong>{node.name}</strong>
            <small>
              {kindLabel[node.kind]} · {node.size ?? "--"}
            </small>
          </div>
          <time>{node.updatedAt ?? "--:--"}</time>
        </div>
      );
    });
  }

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-brand">
          <div className="workspace-brand__mark workspace-brand__mark--image">
            <Image src="/miaojing.png" alt="THIRDEYE logo" width={44} height={44} className="workspace-brand__logo" />
          </div>
          <div>
            <strong>三眼Agent</strong>
            <span>THIRDEYE</span>
          </div>
        </div>

        <button type="button" className="workspace-primary-action" onClick={handleStartNewConversation}>
          <span>＋</span>
          新建对话
          <small>⌘N</small>
        </button>

        <div className="workspace-search">
          <input placeholder="搜索对话或空间" value="" readOnly />
          <button type="button">⚙</button>
        </div>

        <div className="workspace-menu">
          <button type="button" className="workspace-menu__item workspace-menu__item--active">
            <span>◉</span>
            <div>
              <strong>技术评审</strong>
              <small>系统架构与方案评审</small>
            </div>
          </button>
          <button type="button" className="workspace-menu__item">
            <span>◎</span>
            <div>
              <strong>需求拆解</strong>
              <small>需求分析与分解</small>
            </div>
          </button>
          <button type="button" className="workspace-menu__item">
            <span>◌</span>
            <div>
              <strong>风险扫描</strong>
              <small>潜在风险识别与评估</small>
            </div>
          </button>
          <button type="button" className="workspace-menu__item">
            <span>▣</span>
            <div>
              <strong>评审纪要</strong>
              <small>评审结论与跟踪</small>
            </div>
          </button>
        </div>

        <div className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <span>项目空间</span>
            <button type="button" onClick={() => setShowProjectCreator((current) => !current)}>
              ＋
            </button>
          </div>

          {showProjectCreator ? (
            <div className="workspace-project-creator">
              <input
                value={newProjectName}
                onChange={(event) => setNewProjectName(event.target.value)}
                placeholder="项目名称"
              />
              <input
                value={newProjectPath}
                onChange={(event) => setNewProjectPath(event.target.value)}
                placeholder="项目路径，例如 F:\\repo\\service"
              />
              <button type="button" onClick={handleCreateProject} disabled={isPending}>
                {isPending ? "创建中..." : "新增项目"}
              </button>
            </div>
          ) : null}

          <div className="workspace-project-list">
            {workspaceProjects.slice(0, 8).map((project) => (
              <button
                key={project.id}
                type="button"
                className={`workspace-project-item ${
                  selectedProjectId === project.id ? "workspace-project-item--active" : ""
                }`}
                onClick={() => setSelectedProjectId(project.id)}
              >
                <span>▣</span>
                <div className="workspace-project-item__body">
                  <strong>{project.name}</strong>
                  {selectedProjectId === project.id ? <small>当前空间</small> : null}
                </div>
                <button
                  type="button"
                  className="workspace-project-item__delete"
                  aria-label={`删除项目 ${project.name}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    handleDeleteProject(project.id);
                  }}
                >
                  ×
                </button>
              </button>
            ))}
          </div>
        </div>

        <div className="workspace-knowledge-card">
          <div className="workspace-knowledge-card__header">
            <strong>接入企业知识库</strong>
            <span>已连接</span>
          </div>
          <p>知识库：三眼公司知识库 v2.1</p>
          <small>更新时间：2024-05-20 14:32</small>
          <button type="button">管理知识库</button>
        </div>
      </aside>

      <div className="workspace-main">
        <header className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>{activeAgentName?.trim() || "三眼技术评审通用 Agent"}</strong>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button">智能体中心</button>
            <button type="button">⟳</button>
            <button type="button">◐</button>
          </div>
        </header>

        <div className="workspace-hero">
          <div className="workspace-orbit">
            <div className="workspace-orbit__ring workspace-orbit__ring--outer" />
            <div className="workspace-orbit__ring workspace-orbit__ring--inner" />
            <div className="workspace-orbit__core">◉</div>
            <div className="workspace-orbit__node workspace-orbit__node--left">◉</div>
            <div className="workspace-orbit__node workspace-orbit__node--right">◉</div>
          </div>
          <h1>今天要评审什么？</h1>
          <p>三眼 Agent 将从结构、风险、实现三个维度为你提供专业连续评审。</p>
        </div>

        <div className="workspace-capabilities">
          {capabilityCards.map((item) => (
            <article key={item.title} className={`workspace-capability workspace-capability--${item.tone}`}>
              <span className="workspace-capability__badge">◉</span>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </article>
          ))}
        </div>

        <div ref={chatRef} className="workspace-chat">
          {!session ? (
            <article className="workspace-message workspace-message--assistant workspace-message--welcome">
              <div className="workspace-avatar">◉</div>
              <div className="workspace-message__body">
                <strong>三眼 Agent</strong>
                <p>可以直接输入技术方案、重构计划或上线文档，我会启动多轮评审会话并持续记住上下文。</p>
                <div className="workspace-starters">
                  {starterPrompts.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => setDraft(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ) : null}

          {mappedMessages.map((message, index) => (
            <article
              key={message.id}
              className={`workspace-message ${
                message.role === "assistant"
                  ? "workspace-message--assistant"
                  : message.role === "tool" || message.role === "llm"
                    ? "workspace-message--tool"
                    : "workspace-message--user"
              }`}
            >
              <div className="workspace-avatar">
                {message.role === "assistant" ? "◉" : message.role === "llm" ? "◎" : message.role === "tool" ? "⚙" : "你"}
              </div>
              <div className="workspace-message__body">
                <div className="workspace-message__meta">
                  <strong>
                    {message.role === "assistant"
                      ? "三眼 Agent"
                      : message.role === "llm"
                        ? `模型 · ${message.providerId ?? "provider"} / ${message.modelName ?? "model"}`
                      : message.role === "tool"
                        ? `工具 · ${message.toolName ?? "未知工具"}`
                        : "你"}
                  </strong>
                  <div className="workspace-message__meta-actions">
                    <span>{message.timestamp}</span>
                    {message.role === "assistant" ? (
                      <button
                        type="button"
                        className={`workspace-copy-button ${
                          copiedMessageId === message.id ? "workspace-copy-button--copied" : ""
                        }`}
                        onClick={() => void handleCopyMessage(message.id, message.content)}
                        aria-label="复制当前回复"
                      >
                        {copiedMessageId === message.id ? "已复制" : "复制"}
                      </button>
                    ) : null}
                  </div>
                </div>
                {message.role === "tool" || message.role === "llm" ? (
                  <div className="workspace-tool-call">
                    <p>{statusIcon(message.callStatus)} {message.content}</p>
                    {message.role === "llm" && message.toolResult ? (
                      <MarkdownMessage content={message.toolResult} />
                    ) : null}
                    <details className="workspace-tool-call__details">
                      <summary>调用参数</summary>
                      <pre>{message.toolArguments || "(无参数)"}</pre>
                    </details>
                    <details className="workspace-tool-call__details">
                      <summary>执行结果</summary>
                      <pre>{message.toolResult || "(无结果)"}</pre>
                    </details>
                  </div>
                ) : (
                  <MarkdownMessage content={message.content} />
                )}
              </div>
            </article>
          ))}
        </div>

        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
        {session?.resume_available && !isSending ? (
          <p className="workspace-status">
            当前会话存在可恢复断点（{session.resume_reason ? resumeReasonLabel[session.resume_reason] : "可继续执行"}）。
            <button type="button" onClick={() => void handleResumeSession()}>
              继续执行
            </button>
          </p>
        ) : null}

        <div className="workspace-composer">
          <textarea
            ref={draftTextareaRef}
            rows={4}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleDraftKeyDown}
            placeholder="输入技术评审问题，也可以直接写“使用技能：xxx”，Agent 会基于当前项目空间和资料库持续多轮对话。"
          />
          <div className="workspace-composer__footer">
            <div className="workspace-composer__actions">
              <button type="button" onClick={handleOpenKnowledgeUploadPicker}>
                上传文档
              </button>
              <button type="button">扫描风险</button>
              <button type="button">生成结论</button>
            </div>
            <div className="workspace-composer__submit">
              <label className="workspace-composer__control">
                <span>技能</span>
                <select
                  value={selectedSkillName}
                  onChange={(event) => {
                    const nextSkillName = event.target.value;
                    setSelectedSkillName(nextSkillName);
                    if (!nextSkillName) {
                      return;
                    }
                    const selectedSkill = skills.find((skill) => skill.name === nextSkillName);
                    setDraft((current) =>
                      current.trim()
                        ? `${current}\n使用技能：${nextSkillName}`
                        : `使用技能：${nextSkillName}${selectedSkill?.description ? `\n${selectedSkill.description}` : ""}`
                    );
                  }}
                >
                  <option value="">不指定技能</option>
                  {skills.map((skill) => (
                    <option key={skill.name} value={skill.name}>
                      {skill.name}
                    </option>
                  ))}
                </select>
              </label>
              <div
                className={`workspace-context-meter ${contextUsage ? "" : "workspace-context-meter--idle"}`}
                tabIndex={0}
              >
                <div
                  className="workspace-context-meter__ring"
                  style={{
                    background: `conic-gradient(var(--blue) ${contextUsage?.usage_percent ?? 0}%, rgba(203, 213, 225, 0.72) 0)`
                  }}
                >
                  <div className="workspace-context-meter__core">
                    <span>{contextUsage?.usage_percent ?? 0}%</span>
                  </div>
                </div>
                <div className="workspace-context-meter__popover">
                  <div className="workspace-context-meter__popover-head">
                    <div>
                      <strong>上下文</strong>
                      <span>{contextUsage?.provider_name ?? selectedModelProvider?.name ?? "未选择模型"}</span>
                    </div>
                    <strong>{contextUsage?.usage_percent ?? 0}%</strong>
                  </div>
                  <div className="workspace-context-meter__stats">
                    <div>
                      <span>已使用</span>
                      <strong>{formatInteger(contextUsage?.used_tokens ?? 0)}</strong>
                    </div>
                    <div>
                      <span>剩余</span>
                      <strong>{formatInteger(contextUsage?.remaining_tokens ?? 0)}</strong>
                    </div>
                    <div>
                      <span>窗口</span>
                      <strong>{formatInteger(contextUsage?.context_window ?? 0)}</strong>
                    </div>
                  </div>
                  <div className="workspace-context-meter__breakdown">
                    <div>
                      <span>Messages</span>
                      <strong>{formatInteger(contextUsage?.breakdown.messages_tokens ?? 0)}</strong>
                    </div>
                    <div>
                      <span>System prompt</span>
                      <strong>{formatInteger(contextUsage?.breakdown.system_prompt_tokens ?? 0)}</strong>
                    </div>
                    <div>
                      <span>Playbook</span>
                      <strong>{formatInteger(contextUsage?.breakdown.playbook_tokens ?? 0)}</strong>
                    </div>
                  </div>
                  <p className="workspace-context-meter__hint">
                    {contextUsage
                      ? `估算值，更新于 ${formatTime(contextUsage.updated_at)}`
                      : "开始会话后显示当前上下文估算占用"}
                  </p>
                </div>
              </div>
              <label className="workspace-composer__control">
                <span>模型</span>
                <select
                  value={selectedModelProviderId}
                  onChange={(event) => setSelectedModelProviderId(event.target.value)}
                >
                  <option value="">deterministic fallback</option>
                  {modelProviders.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={isSending ? false : isPending || !selectedPlaybookId || !draft.trim()}
                onClick={() => {
                  if (isSending) {
                    void handleStopSession();
                    return;
                  }
                  if (session?.resume_available && !draft.trim()) {
                    void handleResumeSession();
                    return;
                  }
                  void handlePromptSubmit(draft);
                }}
              >
                {isSending ? "终止" : session?.resume_available && !draft.trim() ? "继续" : "➜"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <aside className="workspace-rightbar">
        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>资料区</strong>
              <span>{knowledgeBinding?.effective_root_path ?? "未设置资料区"}</span>
            </div>
            <button type="button">⋯</button>
          </div>

          <div className="workspace-knowledge-actions">
            <button type="button" onClick={() => void handlePickKnowledgeFolder("global")}>
              设置全局资料区
            </button>
            <button type="button" disabled={!selectedProjectId} onClick={() => void handlePickKnowledgeFolder("project")}>
              切换当前项目资料区
            </button>
            <button
              type="button"
              disabled={!selectedProjectId || knowledgeBinding?.scope !== "project"}
              onClick={() => void handleClearProjectKnowledgeOverride()}
            >
              恢复全局资料区
            </button>
          </div>

          <div className="workspace-doc-tabs">
            <button type="button" className="workspace-doc-tabs__active">
              全部
            </button>
            <button type="button">文件 {knowledgeListing?.total_items ?? knowledgeGroups.reduce((acc, [, items]) => acc + items.length, 0)}</button>
            <button type="button">作用域 {knowledgeBinding?.scope === "project" ? "项目" : knowledgeBinding?.scope === "global" ? "全局" : "未配置"}</button>
            <button type="button">{knowledgeBinding?.exists ? "已连接" : "未连接"}</button>
          </div>

          <div className="workspace-doc-search">
            <input
              placeholder="搜索资料"
              value={knowledgeQuery}
              onChange={(event) => setKnowledgeQuery(event.target.value)}
            />
            <button type="button">☰</button>
          </div>

          <div className="workspace-doc-tree">
            {isKnowledgeLoading ? <p className="workspace-empty">资料区加载中...</p> : null}
            {!isKnowledgeLoading && !knowledgeBinding?.effective_root_path ? (
              <p className="workspace-empty">还没有配置资料区。先设置全局资料区，或为当前项目单独切换文件夹。</p>
            ) : null}
            {!isKnowledgeLoading && knowledgeBinding?.effective_root_path && !knowledgeGroups.length ? (
              <p className="workspace-empty">当前资料区没有匹配文件。</p>
            ) : null}
            {renderKnowledgeNodes(knowledgeTree)}
          </div>

          <label className="workspace-upload">
            ＋ 上传资料
            <input
              ref={knowledgeUploadInputRef}
              key={knowledgeUploadInputKey}
              type="file"
              multiple
              hidden
              onChange={(event) => void handleKnowledgeUpload(event)}
            />
          </label>
        </section>

        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>评审结论</strong>
              <span>{session?.last_review?.overall_judgement ?? "草稿"}</span>
            </div>
            <button type="button">✎</button>
          </div>

          <div className="workspace-summary">
            <h3>一、方案概述</h3>
            <p>{reviewSummary.overview}</p>

            <h3>二、关键结论</h3>
            <ul>
              <li>高风险：{reviewSummary.riskCounts.blocker + reviewSummary.riskCounts.major}</li>
              <li>中风险：{reviewSummary.riskCounts.minor}</li>
              <li>当前会话：{session ? `${mappedMessages.length} 条消息` : "尚未开始"}</li>
            </ul>

            <h3>三、建议行动</h3>
            <ul>
              {reviewSummary.recommendations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="workspace-summary__footer">
            <span>更新于 {session ? formatTime(session.updated_at) : "--:--"}</span>
            {session && selectedPlaybookId ? (
              <div className="workspace-summary__links">
                <Link
                  href={`/review/report?session_id=${encodeURIComponent(session.id)}&playbook_id=${encodeURIComponent(selectedPlaybookId)}&mode=markdown`}
                  className="workspace-summary__link"
                >
                  Markdown编辑
                </Link>
                <Link
                  href={`/review/report?session_id=${encodeURIComponent(session.id)}&playbook_id=${encodeURIComponent(selectedPlaybookId)}&mode=document`}
                  className="workspace-summary__link"
                >
                  文档评审
                </Link>
              </div>
            ) : (
              <button type="button" disabled>
                待确认
              </button>
            )}
          </div>
        </section>

        <section className="workspace-panel workspace-panel--history">
          <div className="workspace-panel__header">
            <div>
              <strong>最近会话</strong>
              <span>支持继续多轮追问</span>
            </div>
          </div>
          <div className="workspace-session-list">
            {sessionHistory.length ? (
              sessionHistory.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`workspace-session-item ${session?.id === item.id ? "workspace-session-item--active" : ""}`}
                  onClick={() => {
                    startTransition(async () => {
                      const loaded = await getReviewSession(item.id);
                      connectSessionEvents(item.id);
                      setSession(loaded);
                    });
                  }}
                >
                  <strong>{item.latest_summary ?? item.last_review?.overall_judgement ?? item.id}</strong>
                  <small>
                    {item.mode} · {formatTime(item.updated_at)}
                  </small>
                </button>
              ))
            ) : (
              <p className="workspace-empty">发起第一次对话后，这里会保留最近会话，方便继续追问。</p>
            )}
          </div>
        </section>
      </aside>
    </section>
  );
}
