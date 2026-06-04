"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import { MarkdownMessage } from "@/components/MarkdownMessage";
import type {
  BusinessAgentConfig,
  CodeReviewChangedFile,
  CodeReviewFileDiffResponse,
  CodeReviewProjectFile,
  CodeReviewResponse,
  ModelProviderConfig,
  PlaybookMetadata,
  Project,
  ReviewConversationSession,
  ReviewResponse,
  ReviewSessionEvent
} from "@/lib/api";
import {
  createCodeReview,
  createReviewSession,
  getCodeReviewFileDiff,
  getReviewSessionEventsUrl,
  listCodeReviewBranches,
  listCodeReviewChanges,
  listCodeReviewProjectFiles,
  resumeReviewSession,
  sendReviewMessage,
  stopReviewSession
} from "@/lib/api";

type CodeReviewWorkspaceProps = {
  playbooks: PlaybookMetadata[];
  modelProviders: ModelProviderConfig[];
  projects: Project[];
  codeReviewAgent: BusinessAgentConfig | null;
};

type FileMode = "all" | "diff";

type ReviewFileEntry = {
  id: string;
  name: string;
  path: string;
  directory: string;
  added: number;
  removed: number;
  status: CodeReviewChangedFile["status"];
  language?: string | null;
  sizeBytes?: number;
  patch?: string;
  source: FileMode;
};

type DiffLine = {
  oldLine?: number;
  newLine?: number;
  marker: "context" | "add" | "remove" | "meta";
  code: string;
};

const codeReviewAgentId = "code-review-agent";

const aiActions = [
  "分析代码变更影响",
  "检查代码质量问题",
  "识别潜在风险",
  "生成评审总结"
];

const quickPrompts = [
  "请分析一下当前代码变更的整体质量",
  "重点检查错误处理、权限边界和状态管理是否存在回归风险",
  "请基于当前 diff 输出一份评审结论和建议修改点"
];

const initialAssistantMessage = [
  "我已经准备好评审当前变更。",
  "",
  "重点会检查：",
  "- 行为回归与边界条件",
  "- 参数校验和错误处理",
  "- 测试覆盖与可观测性缺口"
].join("\n");

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function statusLabel(status: CodeReviewChangedFile["status"]) {
  if (status === "added") return "新增";
  if (status === "deleted") return "删除";
  if (status === "renamed") return "重命名";
  if (status === "copied") return "复制";
  if (status === "modified") return "修改";
  return "文件";
}

function fileNameFromPath(path: string) {
  return path.split("/").filter(Boolean).at(-1) ?? path;
}

function directoryFromPath(path: string) {
  const parts = path.split("/").filter(Boolean);
  parts.pop();
  return parts.length ? parts.join("/") : "根目录";
}

function iconForFile(language: string | null | undefined, path: string) {
  const suffix = path.split(".").at(-1)?.toLowerCase() ?? "";
  if (language === "json" || suffix === "json") return "{}";
  if (language === "markdown" || suffix === "md") return "MD";
  if (language === "python" || suffix === "py") return "PY";
  if (language === "javascript" || suffix === "js" || suffix === "jsx") return "JS";
  if (language === "typescript" || suffix === "ts" || suffix === "tsx") return "TS";
  if (suffix === "yml" || suffix === "yaml") return "YML";
  return suffix ? suffix.slice(0, 3).toUpperCase() : "F";
}

function formatBytes(value: number | undefined) {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function toDiffEntry(file: CodeReviewChangedFile): ReviewFileEntry {
  return {
    id: file.path,
    name: fileNameFromPath(file.path),
    path: file.path,
    directory: directoryFromPath(file.path),
    added: file.additions,
    removed: file.deletions,
    status: file.status,
    language: file.language,
    patch: file.patch,
    source: "diff"
  };
}

function toProjectEntry(file: CodeReviewProjectFile): ReviewFileEntry {
  return {
    id: file.path,
    name: file.name,
    path: file.path,
    directory: file.directory,
    added: 0,
    removed: 0,
    status: "unknown",
    language: file.language,
    sizeBytes: file.size_bytes,
    source: "all"
  };
}

function groupFilesByDirectory(files: ReviewFileEntry[]) {
  const groups = new Map<string, ReviewFileEntry[]>();
  for (const file of files) {
    const group = groups.get(file.directory) ?? [];
    group.push(file);
    groups.set(file.directory, group);
  }
  return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right));
}

function chooseDefaultBase(branches: string[], currentBranch: string | null | undefined) {
  const preferred = ["main", "master", "develop", "dev"];
  for (const branch of preferred) {
    if (branch !== currentBranch && branches.includes(branch)) {
      return branch;
    }
  }
  return branches.find((branch) => branch !== currentBranch) ?? currentBranch ?? branches[0] ?? "";
}

function parseUnifiedDiff(patch: string): DiffLine[] {
  const lines: DiffLine[] = [];
  let oldLine: number | undefined;
  let newLine: number | undefined;

  for (const rawLine of patch.split("\n")) {
    const hunk = rawLine.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      lines.push({ marker: "meta", code: rawLine });
      continue;
    }

    if (
      rawLine.startsWith("diff --git") ||
      rawLine.startsWith("index ") ||
      rawLine.startsWith("--- ") ||
      rawLine.startsWith("+++ ") ||
      rawLine.startsWith("new file mode") ||
      rawLine.startsWith("deleted file mode") ||
      rawLine.startsWith("rename ")
    ) {
      lines.push({ marker: "meta", code: rawLine });
      continue;
    }

    if (rawLine.startsWith("+")) {
      lines.push({ newLine, marker: "add", code: rawLine.slice(1) });
      if (newLine !== undefined) newLine += 1;
      continue;
    }

    if (rawLine.startsWith("-")) {
      lines.push({ oldLine, marker: "remove", code: rawLine.slice(1) });
      if (oldLine !== undefined) oldLine += 1;
      continue;
    }

    if (rawLine.startsWith(" ")) {
      lines.push({ oldLine, newLine, marker: "context", code: rawLine.slice(1) });
      if (oldLine !== undefined) oldLine += 1;
      if (newLine !== undefined) newLine += 1;
      continue;
    }

    lines.push({ marker: "meta", code: rawLine });
  }

  return lines;
}

function contentToDiffLines(content: string): DiffLine[] {
  return content.split("\n").map((line, index) => ({
    newLine: index + 1,
    marker: "context",
    code: line
  }));
}

function fileToDiffText(file: ReviewFileEntry | null, detail: CodeReviewFileDiffResponse | null) {
  if (detail?.patch.trim()) return detail.patch;
  if (file?.patch?.trim()) return file.patch;
  if (detail?.content) {
    return detail.content
      .split("\n")
      .map((line) => ` ${line}`)
      .join("\n");
  }
  return "";
}

function buildReviewContext(
  selectedFile: ReviewFileEntry | null,
  detail?: CodeReviewFileDiffResponse | null,
  note?: string
) {
  const diffText = fileToDiffText(selectedFile, detail);

  return [
    "请以代码评审智能体身份评审当前变更。",
    "",
    "[评审目标]",
    "- 先列出高风险问题和行为回归风险",
    "- 再给出测试缺口、可观测性建议和是否可通过结论",
    "- 如无明确问题，也要说明残余风险",
    "",
    "[当前文件]",
    selectedFile
      ? `${selectedFile.path} (+${detail?.additions ?? selectedFile.added} / -${detail?.deletions ?? selectedFile.removed})`
      : "(未选择文件)",
    "",
    "[Diff]",
    "```diff",
    diffText || "(当前文件在所选分支范围内无 diff，可能是未变更文件或仅显示内容预览。)",
    "```",
    "",
    note ? `[评审者补充]\n${note}` : ""
  ]
    .filter(Boolean)
    .join("\n");
}

function summariseReview(review: ReviewResponse | null | undefined) {
  if (!review) {
    return {
      score: "--",
      quality: "等待评审",
      strengths: ["选择项目目录和分支后，系统会加载真实文件与 diff"],
      risks: ["完成评审后展示后端生成的风险、测试缺口和通过结论"]
    };
  }

  return {
    score: review.overall_judgement === "通过" ? "9.0" : review.overall_judgement === "有条件通过" ? "8.0" : "6.5",
    quality: review.overall_judgement,
    strengths: review.suggested_changes.slice(0, 3).length
      ? review.suggested_changes.slice(0, 3)
      : ["已生成结构化评审建议"],
    risks: review.required_validation.slice(0, 3).length
      ? review.required_validation.slice(0, 3)
      : review.key_risks.slice(0, 3)
  };
}

export function CodeReviewWorkspace({
  playbooks,
  modelProviders,
  projects,
  codeReviewAgent
}: CodeReviewWorkspaceProps) {
  const filteredProjects = useMemo(
    () => projects.filter((project) => project.name !== "Sample Project"),
    [projects]
  );
  const projectOptions = useMemo(
    () => (filteredProjects.length ? filteredProjects : projects),
    [filteredProjects, projects]
  );
  const [selectedProjectId, setSelectedProjectId] = useState(filteredProjects[0]?.id ?? projects[0]?.id ?? "");
  const [selectedPlaybookId, setSelectedPlaybookId] = useState(playbooks[0]?.id ?? "");
  const [selectedModelProviderId, setSelectedModelProviderId] = useState(modelProviders[0]?.id ?? "");
  const [fileMode, setFileMode] = useState<FileMode>("diff");
  const [searchQuery, setSearchQuery] = useState("");
  const [branches, setBranches] = useState<string[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string | null>(null);
  const [baseRef, setBaseRef] = useState("");
  const [headRef, setHeadRef] = useState("");
  const [projectFiles, setProjectFiles] = useState<CodeReviewProjectFile[]>([]);
  const [diffFiles, setDiffFiles] = useState<CodeReviewChangedFile[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState("");
  const [selectedFileDiff, setSelectedFileDiff] = useState<CodeReviewFileDiffResponse | null>(null);
  const [isLoadingProjectData, setIsLoadingProjectData] = useState(false);
  const [isLoadingDiffFiles, setIsLoadingDiffFiles] = useState(false);
  const [isLoadingSelectedFile, setIsLoadingSelectedFile] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [session, setSession] = useState<ReviewConversationSession | null>(null);
  const [codeReviewResult, setCodeReviewResult] = useState<CodeReviewResponse | null>(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [reviewNote, setReviewNote] = useState("请重点关注行为回归、错误处理、测试覆盖和安全风险。");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  const chatRef = useRef<HTMLDivElement | null>(null);

  const selectedProject = useMemo(
    () => projectOptions.find((project) => project.id === selectedProjectId) ?? projectOptions[0] ?? null,
    [projectOptions, selectedProjectId]
  );
  const diffEntries = useMemo(() => diffFiles.map(toDiffEntry), [diffFiles]);
  const projectEntries = useMemo(() => projectFiles.map(toProjectEntry), [projectFiles]);
  const activeEntries = fileMode === "diff" ? diffEntries : projectEntries;
  const visibleEntries = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return activeEntries;
    return activeEntries.filter(
      (file) =>
        file.path.toLowerCase().includes(query) ||
        file.name.toLowerCase().includes(query) ||
        file.directory.toLowerCase().includes(query)
    );
  }, [activeEntries, searchQuery]);
  const groupedFiles = useMemo(() => groupFilesByDirectory(visibleEntries), [visibleEntries]);
  const selectedFile = useMemo(
    () =>
      activeEntries.find((file) => file.path === selectedFilePath) ??
      diffEntries.find((file) => file.path === selectedFilePath) ??
      projectEntries.find((file) => file.path === selectedFilePath) ??
      null,
    [activeEntries, diffEntries, projectEntries, selectedFilePath]
  );
  const projectScopedPlaybooks = useMemo(() => {
    if (!selectedProject) return playbooks;
    const scoped = playbooks.filter((playbook) => playbook.project_id === selectedProject.id);
    return scoped.length ? scoped : playbooks;
  }, [playbooks, selectedProject]);
  const reviewTargetFiles = useMemo<CodeReviewChangedFile[]>(() => {
    if (fileMode === "diff") {
      return diffFiles.filter((file) => file.patch.trim());
    }
    if (!selectedFileDiff?.patch.trim() || !selectedFile) {
      return [];
    }
    return [
      {
        path: selectedFileDiff.path,
        status: selectedFileDiff.status,
        additions: selectedFileDiff.additions,
        deletions: selectedFileDiff.deletions,
        patch: selectedFileDiff.patch,
        language: selectedFileDiff.language ?? selectedFile.language
      }
    ];
  }, [diffFiles, fileMode, selectedFile, selectedFileDiff]);
  const diffTotals = useMemo(
    () => ({
      additions: diffFiles.reduce((total, file) => total + file.additions, 0),
      deletions: diffFiles.reduce((total, file) => total + file.deletions, 0)
    }),
    [diffFiles]
  );
  const displayedDiffLines = useMemo(() => {
    if (selectedFileDiff?.patch.trim()) {
      return parseUnifiedDiff(selectedFileDiff.patch);
    }
    if (selectedFileDiff?.content) {
      return contentToDiffLines(selectedFileDiff.content);
    }
    return [];
  }, [selectedFileDiff]);
  const reviewSummary = useMemo(
    () => summariseReview(session?.last_review ?? codeReviewResult?.review),
    [codeReviewResult?.review, session?.last_review]
  );
  const chatMessages = useMemo(() => {
    if (!session) {
      return [
        {
          id: "welcome",
          role: "assistant" as const,
          content: initialAssistantMessage,
          created_at: new Date().toISOString(),
          call_status: null
        }
      ];
    }
    return session.messages.filter((message) => message.role !== "system");
  }, [session]);

  useEffect(() => {
    if (!projectOptions.length) {
      setSelectedProjectId("");
      return;
    }
    if (!projectOptions.some((project) => project.id === selectedProjectId)) {
      setSelectedProjectId(projectOptions[0].id);
    }
  }, [projectOptions, selectedProjectId]);

  useEffect(() => {
    if (!projectScopedPlaybooks.find((playbook) => playbook.id === selectedPlaybookId)) {
      setSelectedPlaybookId(projectScopedPlaybooks[0]?.id ?? "");
    }
  }, [projectScopedPlaybooks, selectedPlaybookId]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId) {
      setBranches([]);
      setCurrentBranch(null);
      setProjectFiles([]);
      setDiffFiles([]);
      setSelectedFilePath("");
      setSelectedFileDiff(null);
      return;
    }

    setIsLoadingProjectData(true);
    setError(null);

    async function loadProjectData() {
      const [branchResult, fileResult] = await Promise.allSettled([
        listCodeReviewBranches({ project_id: selectedProjectId }),
        listCodeReviewProjectFiles({ project_id: selectedProjectId, limit: 1200 })
      ]);
      if (cancelled) return;

      if (branchResult.status === "fulfilled") {
        const nextBranches = branchResult.value.branches;
        const nextHead = branchResult.value.current_branch ?? nextBranches[0] ?? "";
        setBranches(nextBranches);
        setCurrentBranch(branchResult.value.current_branch ?? null);
        setHeadRef(nextHead);
        setBaseRef(chooseDefaultBase(nextBranches, nextHead));
      } else {
        setBranches([]);
        setCurrentBranch(null);
        setHeadRef("");
        setBaseRef("");
        setFileMode("all");
        setError(branchResult.reason instanceof Error ? branchResult.reason.message : "项目分支读取失败，已切换到全部文件模式。");
      }

      if (fileResult.status === "fulfilled") {
        setProjectFiles(fileResult.value.files);
      } else {
        setProjectFiles([]);
        setError(fileResult.reason instanceof Error ? fileResult.reason.message : "项目文件读取失败。");
      }

      setCodeReviewResult(null);
      setIsLoadingProjectData(false);
    }

    void loadProjectData();
    return () => {
      cancelled = true;
    };
  }, [reloadToken, selectedProjectId]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId || !baseRef || !headRef || baseRef === headRef) {
      setDiffFiles([]);
      return;
    }

    setIsLoadingDiffFiles(true);
    listCodeReviewChanges({
      project_id: selectedProjectId,
      base_ref: baseRef,
      head_ref: headRef,
      include_patch: true
    })
      .then((response) => {
        if (cancelled) return;
        setDiffFiles(response.changed_files);
      })
      .catch((caughtError: unknown) => {
        if (cancelled) return;
        setDiffFiles([]);
        setError(caughtError instanceof Error ? caughtError.message : "分支 Diff 读取失败。");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingDiffFiles(false);
      });

    return () => {
      cancelled = true;
    };
  }, [baseRef, headRef, reloadToken, selectedProjectId]);

  useEffect(() => {
    if (selectedFilePath && activeEntries.some((file) => file.path === selectedFilePath)) {
      return;
    }
    setSelectedFilePath(activeEntries[0]?.path ?? "");
  }, [activeEntries, selectedFilePath]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedProjectId || !selectedFilePath) {
      setSelectedFileDiff(null);
      return;
    }

    setIsLoadingSelectedFile(true);
    getCodeReviewFileDiff({
      project_id: selectedProjectId,
      path: selectedFilePath,
      base_ref: baseRef || null,
      head_ref: headRef || null,
      include_content: true
    })
      .then((response) => {
        if (!cancelled) setSelectedFileDiff(response);
      })
      .catch((caughtError: unknown) => {
        if (cancelled) return;
        setSelectedFileDiff(null);
        setError(caughtError instanceof Error ? caughtError.message : "文件对比读取失败。");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSelectedFile(false);
      });

    return () => {
      cancelled = true;
    };
  }, [baseRef, headRef, selectedFilePath, selectedProjectId]);

  useEffect(() => {
    const chatElement = chatRef.current;
    if (!chatElement) return;
    chatElement.scrollTo({ top: chatElement.scrollHeight, behavior: "smooth" });
  }, [chatMessages]);

  function applySessionEvent(sessionId: string, parsed: ReviewSessionEvent) {
    setSession((current) => {
      if (!current || current.id !== sessionId || current.id !== parsed.session_id) {
        return current;
      }
      if (parsed.event_type === "session.snapshot") {
        return parsed.payload as unknown as ReviewConversationSession;
      }

      const next: ReviewConversationSession = { ...current, messages: [...current.messages] };
      const payload = parsed.payload;
      if (typeof payload.status === "string") {
        next.status = payload.status as ReviewConversationSession["status"];
      }
      if ("latest_summary" in payload) {
        next.latest_summary = (payload.latest_summary as string | null | undefined) ?? null;
      }
      if ("last_review" in payload) {
        next.last_review = (payload.last_review as ReviewResponse | null | undefined) ?? null;
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
      if (typeof payload.updated_at === "string") {
        next.updated_at = payload.updated_at;
      }

      const eventMessage = payload.message as ReviewConversationSession["messages"][number] | undefined;
      if (eventMessage?.id) {
        const existingIndex = next.messages.findIndex((message) => message.id === eventMessage.id);
        if (existingIndex >= 0) {
          next.messages[existingIndex] = eventMessage;
        } else {
          next.messages.push(eventMessage);
        }
      }

      return next;
    });
  }

  function connectSessionEvents(sessionId: string) {
    eventSourceRef.current?.close();
    const eventSource = new EventSource(getReviewSessionEventsUrl(sessionId));
    eventSourceRef.current = eventSource;

    const handleMessage = (event: MessageEvent<string>) => {
      try {
        applySessionEvent(sessionId, JSON.parse(event.data) as ReviewSessionEvent);
      } catch {
        // Ignore malformed SSE payloads.
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
      "session.done"
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
    return () => {
      eventSourceRef.current?.close();
      requestAbortRef.current?.abort();
    };
  }, []);

  async function ensureSession() {
    if (session && session.playbook_id === selectedPlaybookId && session.agent_id === codeReviewAgentId) {
      return session;
    }
    const created = await createReviewSession({
      playbook_id: selectedPlaybookId,
      project_id: selectedProjectId || undefined,
      agent_id: codeReviewAgentId,
      mode: "strict",
      ...(selectedModelProviderId ? { model_provider_id: selectedModelProviderId } : {})
    });
    setSession(created);
    connectSessionEvents(created.id);
    return created;
  }

  async function submitToAgent(content: string) {
    if (!selectedPlaybookId || !content.trim()) {
      return;
    }
    setError(null);
    setIsSending(true);
    const controller = new AbortController();
    requestAbortRef.current = controller;
    try {
      const targetSession = await ensureSession();
      setSession((current) =>
        current && current.id === targetSession.id
          ? { ...current, status: "running" }
          : { ...targetSession, status: "running" }
      );
      const updated = await sendReviewMessage(targetSession.id, { message: content.trim() }, controller.signal);
      setSession(updated);
      setMessageDraft("");
    } catch (caughtError) {
      if (caughtError instanceof Error && caughtError.name === "AbortError") {
        setError("已终止当前代码评审请求。");
      } else {
        setError(caughtError instanceof Error ? caughtError.message : "代码评审会话启动失败。");
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
      setError(caughtError instanceof Error ? caughtError.message : "终止会话失败。");
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
      setError(caughtError instanceof Error ? caughtError.message : "继续执行失败。");
    } finally {
      setIsSending(false);
    }
  }

  async function handleRunCodeReview() {
    if (!selectedPlaybookId || !reviewTargetFiles.length) {
      setError("当前没有可评审的分支 Diff。请切换分支或选择有变更的文件。");
      return;
    }
    setError(null);
    setIsSending(true);
    try {
      const result = await createCodeReview({
        playbook_id: selectedPlaybookId,
        project_id: selectedProjectId || undefined,
        agent_id: codeReviewAgentId,
        mode: "strict",
        base_ref: baseRef || null,
        head_ref: headRef || null,
        ...(selectedModelProviderId ? { model_provider_id: selectedModelProviderId } : {}),
        changed_files: reviewTargetFiles,
        focus: ["行为回归", "安全风险", "测试覆盖", "可维护性"],
        reviewer_note: reviewNote
      });
      setCodeReviewResult(result);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "代码评审执行失败。");
    } finally {
      setIsSending(false);
    }
  }

  function handleChatKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void submitToAgent(messageDraft);
    }
  }

  function handleSubmitReviewNote() {
    void submitToAgent(buildReviewContext(selectedFile, selectedFileDiff, reviewNote));
  }

  return (
    <section className="code-review-shell">
      <header className="code-review-topbar">
        <div className="code-review-title">
          <span className="code-review-title__icon">▣</span>
          <strong>代码评审</strong>
          <span>› {selectedProject?.name ?? "未选择项目"} › {fileMode === "diff" ? "分支 Diff" : "全部文件"} › {selectedFile?.path ?? "未选择文件"}</span>
        </div>
        <div className="code-review-topbar__status">
          <span>{isLoadingProjectData || isLoadingDiffFiles ? "正在同步项目" : "已连接真实项目目录"}</span>
          <strong>{currentBranch ?? (headRef || "工作区")}</strong>
        </div>
        <div className="code-review-topbar__actions">
          <select
            aria-label="选择 Playbook"
            value={selectedPlaybookId}
            onChange={(event) => setSelectedPlaybookId(event.target.value)}
          >
            {projectScopedPlaybooks.map((playbook) => (
              <option key={playbook.id} value={playbook.id}>
                {playbook.name}
              </option>
            ))}
          </select>
          <select
            aria-label="选择模型"
            value={selectedModelProviderId}
            onChange={(event) => setSelectedModelProviderId(event.target.value)}
          >
            {modelProviders.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
          <Link className="code-review-ghost-button" href="/settings/agents">
            评审方 · {codeReviewAgent?.name ?? "代码评审 Agent"}
          </Link>
          <button
            className="code-review-primary-button"
            type="button"
            disabled={isSending || !selectedPlaybookId || !reviewTargetFiles.length}
            onClick={handleRunCodeReview}
          >
            {isSending ? "评审中..." : "完成评审"}
          </button>
        </div>
      </header>

      <div className="code-review-grid">
        <aside className="code-review-sidebar">
          <section className="code-review-panel code-review-files">
            <div className="code-review-panel__header">
              <div>
                <strong>{fileMode === "diff" ? `分支 Diff (${diffFiles.length})` : `项目文件 (${projectFiles.length})`}</strong>
                <span>{selectedProject?.root_path ?? "请选择项目目录"}</span>
              </div>
              <button type="button" aria-label="刷新变更" onClick={() => setReloadToken((value) => value + 1)}>
                ⟳
              </button>
            </div>

            <label className="code-review-field">
              <span>项目目录</span>
              <select
                aria-label="选择项目目录"
                value={selectedProjectId}
                onChange={(event) => {
                  setSelectedProjectId(event.target.value);
                  setSelectedFilePath("");
                }}
              >
                {projectOptions.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
              <small>{selectedProject?.root_path ?? "暂无可用项目，请先在项目页添加目录。"}</small>
            </label>

            <div className="code-review-branch-picker">
              <label>
                <span>基准分支</span>
                <select
                  value={baseRef}
                  onChange={(event) => setBaseRef(event.target.value)}
                  disabled={!branches.length}
                >
                  {branches.length ? (
                    branches.map((branch) => (
                      <option key={branch} value={branch}>
                        {branch}
                      </option>
                    ))
                  ) : (
                    <option value="">无 Git 分支</option>
                  )}
                </select>
              </label>
              <label>
                <span>比对分支</span>
                <select
                  value={headRef}
                  onChange={(event) => setHeadRef(event.target.value)}
                  disabled={!branches.length}
                >
                  {branches.length ? (
                    branches.map((branch) => (
                      <option key={branch} value={branch}>
                        {branch}
                      </option>
                    ))
                  ) : (
                    <option value="">工作区</option>
                  )}
                </select>
              </label>
            </div>

            <label className="code-review-search">
              <span>⌕</span>
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="按文件名筛选"
              />
              <em>⌯</em>
            </label>
            <div className="code-review-filter-row">
              <button
                type="button"
                className={fileMode === "all" ? "code-review-filter-row__active" : ""}
                onClick={() => setFileMode("all")}
              >
                全部文件 {projectFiles.length}
              </button>
              <button
                type="button"
                className={fileMode === "diff" ? "code-review-filter-row__active" : ""}
                onClick={() => setFileMode("diff")}
                disabled={!branches.length}
              >
                分支 Diff {diffFiles.length}
              </button>
            </div>

            <div className="code-review-tree">
              <div className="code-review-tree__folder">⌄ {selectedProject?.name ?? "项目"}</div>
              {isLoadingProjectData || (fileMode === "diff" && isLoadingDiffFiles) ? (
                <div className="code-review-empty">正在加载文件...</div>
              ) : groupedFiles.length ? (
                groupedFiles.map(([folder, files]) => (
                  <div key={folder} className="code-review-tree__group">
                    <div className="code-review-tree__folder code-review-tree__folder--nested">⌄ {folder}</div>
                    {files.map((file) => (
                      <button
                        key={`${file.source}-${file.path}`}
                        type="button"
                        className={`code-review-file ${file.path === selectedFilePath ? "code-review-file--active" : ""}`}
                        onClick={() => setSelectedFilePath(file.path)}
                      >
                        <span className="code-review-file__icon">{iconForFile(file.language, file.path)}</span>
                        <strong title={file.path}>{file.name}</strong>
                        {file.source === "diff" ? (
                          <>
                            <em>+{file.added}</em>
                            <b>{file.removed ? `-${file.removed}` : "-0"}</b>
                          </>
                        ) : (
                          <small>{formatBytes(file.sizeBytes)}</small>
                        )}
                      </button>
                    ))}
                  </div>
                ))
              ) : (
                <div className="code-review-empty">
                  {fileMode === "diff" ? "当前分支范围没有变更文件。" : "没有匹配的项目文件。"}
                </div>
              )}
            </div>

            <div className="code-review-file-summary">
              <strong>共 {visibleEntries.length} 个文件</strong>
              {fileMode === "diff" ? (
                <>
                  <span>+{diffTotals.additions}</span>
                  <em>-{diffTotals.deletions}</em>
                  <small>{baseRef || "base"} → {headRef || "head"}</small>
                </>
              ) : (
                <small>点击文件后在中间显示内容或分支对比</small>
              )}
            </div>
          </section>
        </aside>

        <main className="code-review-main">
          <section className="code-review-panel code-review-diff-card">
            <div className="code-review-filebar">
              <div className="code-review-filebar__title">
                <span className="code-review-filebar__doc">▧</span>
                <strong>{selectedFile?.name ?? "未选择文件"}</strong>
                <button type="button" onClick={() => setSelectedFilePath("")}>×</button>
                <em>{selectedFile ? statusLabel(selectedFile.status) : "未选择"}</em>
              </div>
              <div className="code-review-filebar__actions">
                <button type="button" className="code-review-filebar__active">
                  统一 Diff
                </button>
                <button type="button">{selectedFileDiff?.patch.trim() ? "对比模式" : "内容预览"}</button>
                <button type="button">导出评审报告</button>
              </div>
            </div>

            <div className="code-review-branch-row">
              <span>基准分支：</span>
              <strong>{baseRef || "未选择"}</strong>
              <em>→</em>
              <span>比对分支：</span>
              <strong>{headRef || "工作区"}</strong>
              {selectedFile ? <small>{selectedFile.path}</small> : null}
            </div>

            <div className="code-review-diff">
              {isLoadingSelectedFile ? (
                <div className="code-review-empty">正在加载文件对比...</div>
              ) : displayedDiffLines.length ? (
                displayedDiffLines.map((line, index) => (
                  <div key={`${line.marker}-${index}`} className={`code-review-diff__line code-review-diff__line--${line.marker}`}>
                    <span className="code-review-diff__num">{line.oldLine ?? ""}</span>
                    <span className="code-review-diff__num">{line.newLine ?? ""}</span>
                    <span className="code-review-diff__marker">
                      {line.marker === "add" ? "+" : line.marker === "remove" ? "-" : ""}
                    </span>
                    <code>{line.code || " "}</code>
                  </div>
                ))
              ) : (
                <div className="code-review-empty">选择左侧文件后，这里会显示分支 diff 或文件内容。</div>
              )}
            </div>

            <div className="code-review-comment">
              <div className="code-review-comment__author">
                <span>N</span>
                <strong>Nikki</strong>
                <em>评审方</em>
                <small>{reviewTargetFiles.length ? `可评审 ${reviewTargetFiles.length} 个变更文件` : "当前文件无可评审 diff"}</small>
              </div>
              <div className="code-review-comment__body">
                <strong>评审意见：</strong>
                <p>
                  {selectedFileDiff?.patch.trim()
                    ? "已读取真实分支差异，可提交给代码评审智能体分析。"
                    : "当前文件在所选分支范围内没有 diff，中间区域显示内容预览。"}
                </p>
                <strong>建议修改：</strong>
              </div>
              <div className="code-review-editor">
                <div className="code-review-editor__toolbar">
                  <span>B</span>
                  <span>I</span>
                  <span>U</span>
                  <span>⌘</span>
                  <span>↗</span>
                  <span>🔗</span>
                </div>
                <textarea
                  value={reviewNote}
                  onChange={(event) => setReviewNote(event.target.value)}
                  placeholder="输入评审意见或补充说明"
                  maxLength={500}
                />
                <small>{reviewNote.length}/500</small>
              </div>
              <div className="code-review-comment__actions">
                <button type="button" onClick={() => setReviewNote("")}>
                  取消
                </button>
                <button type="button" onClick={handleSubmitReviewNote} disabled={isSending || !reviewNote.trim()}>
                  提交修改
                </button>
              </div>
            </div>
          </section>
        </main>

        <aside className="code-review-ai">
          <section className="code-review-panel code-review-ai-card">
            <div className="code-review-panel__header">
              <div>
                <strong>AI 对话助手</strong>
                <span>{session?.status === "running" ? "正在分析当前 diff" : "已绑定代码评审智能体"}</span>
              </div>
              <button type="button" onClick={session?.resume_available ? handleResumeSession : undefined}>
                {session?.resume_available ? "继续" : "↻"}
              </button>
            </div>

            <div className="code-review-bot-hero">
              <div className="code-review-bot">🤖</div>
              <div className="code-review-bot-card">
                <strong>你好！我是 AI 助手</strong>
                <p>我可以帮你分析代码变更、提供评审建议和修改意见。</p>
                {aiActions.map((action) => (
                  <button key={action} type="button" onClick={() => submitToAgent(`${action}：\n\n${buildReviewContext(selectedFile, selectedFileDiff)}`)}>
                    {action}
                    <span>→</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="code-review-quick-prompts">
              {quickPrompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => submitToAgent(`${prompt}\n\n${buildReviewContext(selectedFile, selectedFileDiff)}`)}>
                  {prompt}
                </button>
              ))}
            </div>

            <div ref={chatRef} className="code-review-chat">
              {chatMessages.map((message) => (
                <article key={message.id} className={`code-review-chat-message code-review-chat-message--${message.role}`}>
                  <span className="code-review-chat-message__avatar">
                    {message.role === "user" ? "你" : message.role === "tool" ? "T" : message.role === "llm" ? "L" : "AI"}
                  </span>
                  <div>
                    <div className="code-review-chat-message__meta">
                      <strong>{message.role === "user" ? "Nikki" : message.role === "assistant" ? "代码评审 Agent" : message.role}</strong>
                      <span>{formatTime(message.created_at)}</span>
                      {message.call_status ? <em>{message.call_status}</em> : null}
                    </div>
                    <MarkdownMessage content={message.content} />
                  </div>
                </article>
              ))}
            </div>

            <div className="code-review-ai-summary">
              <strong>整体质量评估：{reviewSummary.quality} ({reviewSummary.score}/10)</strong>
              {codeReviewResult ? <small>后端评审记录：{codeReviewResult.id}</small> : null}
              <span>主要优点</span>
              <ul>
                {reviewSummary.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <span>主要改进点</span>
              <ul>
                {reviewSummary.risks.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            {error ? <p className="code-review-error">{error}</p> : null}

            <div className="code-review-chatbox">
              <textarea
                value={messageDraft}
                onChange={(event) => setMessageDraft(event.target.value)}
                onKeyDown={handleChatKeyDown}
                placeholder="输入问题，AI 助手为你解答..."
                maxLength={500}
              />
              <div>
                <span>{messageDraft.length}/500</span>
                {isSending ? (
                  <button type="button" onClick={handleStopSession}>
                    停止
                  </button>
                ) : (
                  <button type="button" onClick={() => submitToAgent(messageDraft)} disabled={!messageDraft.trim()}>
                    发送
                  </button>
                )}
              </div>
            </div>
          </section>
        </aside>
      </div>

      <style jsx>{`
        .code-review-shell {
          min-height: calc(100vh - 88px);
          color: #101a35;
          background:
            radial-gradient(circle at 76% 14%, rgba(53, 113, 255, 0.12), transparent 24%),
            radial-gradient(circle at 16% 90%, rgba(76, 201, 156, 0.08), transparent 28%),
            linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
          border: 1px solid rgba(213, 223, 239, 0.92);
          border-radius: 24px;
          box-shadow: 0 28px 80px rgba(38, 68, 118, 0.14);
          overflow: hidden;
        }

        .code-review-topbar {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto minmax(420px, auto);
          align-items: center;
          gap: 18px;
          min-height: 72px;
          padding: 14px 20px;
          border-bottom: 1px solid rgba(213, 223, 239, 0.9);
          background: rgba(255, 255, 255, 0.84);
          backdrop-filter: blur(16px);
        }

        .code-review-title,
        .code-review-topbar__status,
        .code-review-topbar__actions,
        .code-review-filebar,
        .code-review-filebar__title,
        .code-review-filebar__actions,
        .code-review-branch-row,
        .code-review-filter-row,
        .code-review-comment__author,
        .code-review-comment__actions {
          display: flex;
          align-items: center;
        }

        .code-review-title {
          gap: 12px;
          min-width: 0;
          font-size: 0.96rem;
        }

        .code-review-title strong {
          font-size: 1.3rem;
          letter-spacing: -0.04em;
        }

        .code-review-title span:last-child,
        .code-review-topbar__status,
        .code-review-panel__header span,
        .code-review-branch-row span,
        .code-review-comment small,
        .code-review-chat-message__meta span,
        .code-review-chatbox span {
          color: #72819c;
        }

        .code-review-title__icon,
        .code-review-filebar__doc {
          display: grid;
          place-items: center;
          width: 24px;
          height: 24px;
          border-radius: 8px;
          background: #0f62ff;
          color: white;
          box-shadow: 0 10px 24px rgba(15, 98, 255, 0.25);
        }

        .code-review-topbar__status {
          gap: 8px;
          font-size: 0.9rem;
        }

        .code-review-topbar__actions {
          justify-content: flex-end;
          gap: 10px;
          min-width: 0;
        }

        .code-review-topbar select,
        .code-review-ghost-button,
        .code-review-primary-button,
        .code-review-filebar__actions button,
        .code-review-comment__actions button,
        .code-review-chatbox button {
          border: 1px solid rgba(202, 214, 232, 0.9);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.9);
          color: #1b2b4d;
          cursor: pointer;
          transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }

        .code-review-topbar select {
          max-width: 150px;
          padding: 9px 10px;
        }

        .code-review-ghost-button,
        .code-review-primary-button {
          padding: 10px 14px;
          font-weight: 700;
        }

        .code-review-primary-button {
          border-color: #0f62ff;
          background: linear-gradient(135deg, #0f62ff, #0050d8);
          color: white;
          box-shadow: 0 14px 30px rgba(15, 98, 255, 0.22);
        }

        .code-review-primary-button:disabled,
        .code-review-chatbox button:disabled,
        .code-review-comment__actions button:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .code-review-grid {
          display: grid;
          grid-template-columns: 340px minmax(0, 1fr) 360px;
          gap: 14px;
          padding: 14px;
        }

        .code-review-sidebar,
        .code-review-main,
        .code-review-ai {
          min-width: 0;
        }

        .code-review-panel {
          border: 1px solid rgba(213, 223, 239, 0.92);
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.86);
          box-shadow: 0 18px 44px rgba(53, 74, 110, 0.09);
          backdrop-filter: blur(14px);
        }

        .code-review-files,
        .code-review-ai-card {
          display: grid;
          gap: 14px;
          padding: 16px;
        }

        .code-review-panel__header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .code-review-panel__header strong {
          display: block;
          font-size: 1.06rem;
        }

        .code-review-panel__header button {
          width: 32px;
          height: 32px;
          border-radius: 10px;
          border: 1px solid rgba(202, 214, 232, 0.86);
          background: rgba(255, 255, 255, 0.86);
          color: #31517f;
          cursor: pointer;
        }

        .code-review-field,
        .code-review-branch-picker label {
          display: grid;
          gap: 6px;
        }

        .code-review-field span,
        .code-review-branch-picker span {
          color: #536886;
          font-size: 0.8rem;
          font-weight: 800;
        }

        .code-review-field select,
        .code-review-branch-picker select {
          width: 100%;
          min-width: 0;
          padding: 9px 10px;
          border: 1px solid rgba(202, 214, 232, 0.9);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.92);
          color: #1b2b4d;
        }

        .code-review-field small {
          overflow: hidden;
          color: #72819c;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .code-review-branch-picker {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .code-review-search {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          border: 1px solid rgba(202, 214, 232, 0.9);
          border-radius: 12px;
          background: #fbfdff;
        }

        .code-review-search input {
          width: 100%;
          border: 0;
          outline: 0;
          background: transparent;
          color: #1b2b4d;
        }

        .code-review-search span,
        .code-review-search em {
          color: #6e7f9f;
          font-style: normal;
        }

        .code-review-filter-row {
          gap: 8px;
        }

        .code-review-filter-row button {
          padding: 8px 11px;
          border-radius: 10px;
          border: 1px solid rgba(202, 214, 232, 0.72);
          background: rgba(255, 255, 255, 0.82);
          color: #33486d;
          cursor: pointer;
        }

        .code-review-filter-row button:disabled {
          cursor: not-allowed;
          opacity: 0.48;
        }

        .code-review-filter-row__active {
          border-color: rgba(15, 98, 255, 0.18) !important;
          background: #edf4ff !important;
          color: #0f62ff !important;
          font-weight: 700;
        }

        .code-review-tree {
          display: grid;
          gap: 7px;
          max-height: calc(100vh - 330px);
          overflow: auto;
          padding-right: 2px;
        }

        .code-review-tree__group {
          display: grid;
          gap: 4px;
        }

        .code-review-tree__folder {
          color: #1b2b4d;
          font-weight: 700;
          padding: 6px 4px;
        }

        .code-review-tree__folder--nested {
          padding-left: 16px;
          font-weight: 600;
        }

        .code-review-file {
          display: grid;
          grid-template-columns: 22px minmax(0, 1fr) auto auto;
          align-items: center;
          gap: 9px;
          width: 100%;
          padding: 9px 10px 9px 34px;
          border: 1px solid transparent;
          border-radius: 12px;
          background: transparent;
          color: #152341;
          cursor: pointer;
          text-align: left;
        }

        .code-review-file--active {
          border-color: rgba(15, 98, 255, 0.08);
          background: linear-gradient(90deg, rgba(230, 240, 255, 0.98), rgba(243, 248, 255, 0.84));
          box-shadow: inset 3px 0 0 #0f62ff;
        }

        .code-review-file__icon {
          display: grid;
          place-items: center;
          width: 20px;
          height: 20px;
          border-radius: 6px;
          background: #eaf2ff;
          color: #0f62ff;
          font-size: 0.65rem;
          font-weight: 800;
        }

        .code-review-file__icon--sheet {
          background: #e8f8f3;
          color: #14966d;
        }

        .code-review-file strong {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 0.92rem;
        }

        .code-review-file em,
        .code-review-file b {
          font-style: normal;
          font-weight: 700;
        }

        .code-review-file em {
          color: #0c9f72;
        }

        .code-review-file b {
          color: #e0344f;
        }

        .code-review-file small {
          color: #72819c;
          font-size: 0.78rem;
          font-weight: 700;
        }

        .code-review-empty {
          padding: 18px 12px;
          color: #6f80a1;
          text-align: center;
        }

        .code-review-file-summary {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 10px;
          padding-top: 12px;
          border-top: 1px solid rgba(213, 223, 239, 0.88);
          color: #72819c;
        }

        .code-review-file-summary strong {
          color: #1b2b4d;
        }

        .code-review-file-summary span {
          color: #0c9f72;
          font-weight: 800;
        }

        .code-review-file-summary em {
          color: #e0344f;
          font-style: normal;
          font-weight: 800;
        }

        .code-review-diff-card {
          padding: 16px;
        }

        .code-review-filebar {
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 12px;
        }

        .code-review-filebar__title,
        .code-review-filebar__actions {
          gap: 9px;
        }

        .code-review-filebar__title strong {
          color: #0050d8;
          font-size: 1.04rem;
        }

        .code-review-filebar__title button {
          color: #0050d8;
          cursor: pointer;
        }

        .code-review-filebar__title em {
          padding: 6px 10px;
          border-radius: 999px;
          background: #e8f8f3;
          color: #14966d;
          font-size: 0.82rem;
          font-style: normal;
          font-weight: 700;
        }

        .code-review-filebar__actions button {
          padding: 9px 12px;
          font-weight: 700;
        }

        .code-review-filebar__active {
          border-color: rgba(15, 98, 255, 0.16) !important;
          background: #edf4ff !important;
          color: #0f62ff !important;
        }

        .code-review-branch-row {
          gap: 9px;
          margin-bottom: 12px;
        }

        .code-review-branch-row strong {
          color: #1b2b4d;
        }

        .code-review-branch-row em {
          color: #7890b8;
          font-style: normal;
        }

        .code-review-diff {
          overflow: auto;
          border: 1px solid rgba(213, 223, 239, 0.95);
          border-radius: 14px;
          background: #fbfdff;
          font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
          font-size: 0.92rem;
          line-height: 1.65;
        }

        .code-review-diff__line {
          display: grid;
          grid-template-columns: 46px 46px 22px minmax(560px, 1fr);
          min-height: 27px;
        }

        .code-review-diff__line--meta {
          color: #607195;
          background: #f7faff;
        }

        .code-review-diff__line--remove {
          color: #b71d36;
          background: linear-gradient(90deg, rgba(255, 229, 232, 0.88), rgba(255, 241, 243, 0.78));
        }

        .code-review-diff__line--add {
          color: #0a6f50;
          background: linear-gradient(90deg, rgba(225, 248, 238, 0.94), rgba(241, 252, 246, 0.82));
        }

        .code-review-diff__num,
        .code-review-diff__marker {
          color: #6f80a1;
          text-align: right;
          padding-right: 10px;
          user-select: none;
        }

        .code-review-diff__marker {
          text-align: center;
          padding: 0;
          font-weight: 800;
        }

        .code-review-diff code {
          white-space: pre;
          color: inherit;
        }

        .code-review-comment {
          display: grid;
          gap: 12px;
          padding: 14px;
          border: 1px solid rgba(213, 223, 239, 0.9);
          border-top: 0;
          border-radius: 0 0 16px 16px;
          background: #ffffff;
        }

        .code-review-comment__author {
          gap: 10px;
        }

        .code-review-comment__author span,
        .code-review-chat-message__avatar {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: #0f62ff;
          color: white;
          font-size: 0.78rem;
          font-weight: 800;
        }

        .code-review-comment__author em {
          padding: 4px 8px;
          border-radius: 999px;
          background: #edf4ff;
          color: #0f62ff;
          font-style: normal;
          font-size: 0.78rem;
          font-weight: 700;
        }

        .code-review-comment__body {
          display: grid;
          gap: 8px;
        }

        .code-review-comment__body p {
          margin: 0;
          color: #41516f;
        }

        .code-review-editor {
          position: relative;
          border: 1px solid rgba(202, 214, 232, 0.95);
          border-radius: 12px;
          overflow: hidden;
        }

        .code-review-editor__toolbar {
          display: flex;
          gap: 18px;
          padding: 10px 14px;
          border-bottom: 1px solid rgba(202, 214, 232, 0.8);
          color: #4a6088;
          background: #fbfdff;
        }

        .code-review-editor textarea {
          width: 100%;
          min-height: 70px;
          resize: vertical;
          border: 0;
          outline: 0;
          padding: 14px;
          color: #1b2b4d;
        }

        .code-review-editor small {
          position: absolute;
          right: 12px;
          bottom: 8px;
          color: #7d8ba4;
        }

        .code-review-comment__actions {
          justify-content: flex-end;
          gap: 10px;
        }

        .code-review-comment__actions button {
          padding: 9px 16px;
          font-weight: 700;
        }

        .code-review-comment__actions button:last-child {
          border-color: #0f62ff;
          background: #0f62ff;
          color: white;
        }

        .code-review-ai-card {
          max-height: calc(100vh - 106px);
          overflow: hidden;
        }

        .code-review-bot-hero {
          display: grid;
          place-items: center;
          gap: 8px;
          padding: 12px 10px 0;
          background:
            radial-gradient(circle at center top, rgba(15, 98, 255, 0.14), transparent 48%),
            linear-gradient(180deg, rgba(245, 249, 255, 0.96), rgba(255, 255, 255, 0));
          border-radius: 16px;
        }

        .code-review-bot {
          display: grid;
          place-items: center;
          width: 58px;
          height: 58px;
          border-radius: 20px;
          background: linear-gradient(145deg, #1b73ff, #0050d8);
          box-shadow: 0 18px 35px rgba(15, 98, 255, 0.28);
          font-size: 1.75rem;
        }

        .code-review-bot-card {
          display: grid;
          gap: 8px;
          width: 100%;
          padding: 14px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.92);
          box-shadow: 0 14px 34px rgba(53, 74, 110, 0.08);
        }

        .code-review-bot-card p {
          margin: 0;
          color: #52627d;
          line-height: 1.6;
        }

        .code-review-bot-card button,
        .code-review-quick-prompts button {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          width: 100%;
          padding: 10px 12px;
          border: 1px solid rgba(213, 223, 239, 0.88);
          border-radius: 11px;
          background: #fbfdff;
          color: #31517f;
          cursor: pointer;
          text-align: left;
        }

        .code-review-quick-prompts {
          display: grid;
          gap: 8px;
        }

        .code-review-quick-prompts button {
          background: #edf4ff;
          color: #0f62ff;
          font-weight: 700;
        }

        .code-review-chat {
          display: grid;
          gap: 12px;
          min-height: 120px;
          max-height: 260px;
          overflow: auto;
          padding-right: 2px;
        }

        .code-review-chat-message {
          display: grid;
          grid-template-columns: 30px minmax(0, 1fr);
          gap: 10px;
          padding: 12px;
          border-radius: 14px;
          background: #fbfdff;
          border: 1px solid rgba(213, 223, 239, 0.8);
        }

        .code-review-chat-message--user {
          background: #edf4ff;
        }

        .code-review-chat-message--tool,
        .code-review-chat-message--llm {
          opacity: 0.78;
        }

        .code-review-chat-message__meta {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }

        .code-review-chat-message__meta em {
          padding: 2px 7px;
          border-radius: 999px;
          background: #eef3fb;
          color: #536886;
          font-size: 0.72rem;
          font-style: normal;
        }

        .code-review-ai-summary {
          display: grid;
          gap: 8px;
          padding: 14px;
          border-radius: 14px;
          background: #ffffff;
          border: 1px solid rgba(213, 223, 239, 0.86);
        }

        .code-review-ai-summary span {
          color: #8d2938;
          font-weight: 800;
        }

        .code-review-ai-summary ul {
          margin: 0;
          padding-left: 18px;
          color: #263a5c;
          line-height: 1.55;
        }

        .code-review-error {
          margin: 0;
          padding: 10px 12px;
          border-radius: 12px;
          background: rgba(255, 93, 84, 0.09);
          border: 1px solid rgba(255, 93, 84, 0.14);
          color: #b34b46;
        }

        .code-review-chatbox {
          display: grid;
          gap: 10px;
          padding: 12px;
          border: 1px solid rgba(213, 223, 239, 0.95);
          border-radius: 14px;
          background: #fbfdff;
        }

        .code-review-chatbox textarea {
          width: 100%;
          min-height: 68px;
          border: 0;
          outline: 0;
          resize: vertical;
          background: transparent;
          color: #1b2b4d;
        }

        .code-review-chatbox div {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .code-review-chatbox button {
          min-width: 42px;
          height: 34px;
          border-radius: 999px;
          background: #0f62ff;
          color: white;
          font-weight: 800;
        }

        @media (max-width: 1320px) {
          .code-review-topbar {
            grid-template-columns: 1fr;
          }

          .code-review-topbar__actions {
            justify-content: flex-start;
            flex-wrap: wrap;
          }

          .code-review-grid {
            grid-template-columns: 290px minmax(0, 1fr);
          }

          .code-review-ai {
            grid-column: 1 / -1;
          }

          .code-review-ai-card {
            max-height: none;
          }
        }

        @media (max-width: 920px) {
          .code-review-grid {
            grid-template-columns: 1fr;
          }

          .code-review-filebar,
          .code-review-comment__actions,
          .code-review-branch-row {
            align-items: flex-start;
            flex-direction: column;
          }

          .code-review-filebar__actions {
            flex-wrap: wrap;
          }
        }

        @media (max-width: 640px) {
          .code-review-shell {
            border-radius: 18px;
          }

          .code-review-grid,
          .code-review-topbar {
            padding: 10px;
          }

          .code-review-diff__line {
            grid-template-columns: 34px 34px 18px minmax(440px, 1fr);
          }
        }
      `}</style>
    </section>
  );
}
