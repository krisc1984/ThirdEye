"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import type {
  ModelProviderConfig,
  PlaybookDetail,
  PlaybookMetadata,
  Project,
  ReviewConversationSession,
  ReviewResponse,
  SkillListItem
} from "@/lib/api";
import {
  createProject,
  createReviewSession,
  deleteProject,
  getPlaybook,
  getReviewSession,
  resumeReviewSession,
  sendReviewMessage,
  stopReviewSession
} from "@/lib/api";

type AgentWorkspaceProps = {
  playbooks: PlaybookMetadata[];
  modelProviders: ModelProviderConfig[];
  projects: Project[];
  skills: SkillListItem[];
};

type WorkspaceMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
};

type KnowledgeItem = {
  id: string;
  name: string;
  kind: "pdf" | "doc" | "uml" | "sheet" | "folder";
  size: string;
  updatedAt: string;
  folder: string;
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

export function AgentWorkspace({ playbooks, modelProviders, projects, skills }: AgentWorkspaceProps) {
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
  const [session, setSession] = useState<ReviewConversationSession | null>(null);
  const [sessionHistory, setSessionHistory] = useState<ReviewConversationSession[]>([]);
  const [playbookDetail, setPlaybookDetail] = useState<PlaybookDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isPending, startTransition] = useTransition();
  const requestAbortRef = useRef<AbortController | null>(null);
  const chatRef = useRef<HTMLDivElement | null>(null);

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
        role: message.role === "assistant" ? "assistant" : "user",
        content: message.content,
        timestamp: formatTime(message.created_at)
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

  const evidenceKnowledgeItems = useMemo<KnowledgeItem[]>(() => {
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
  }, [playbookDetail]);

  const knowledgeGroups = useMemo(() => {
    const groups = new Map<string, KnowledgeItem[]>();
    for (const item of evidenceKnowledgeItems) {
      const list = groups.get(item.folder) ?? [];
      list.push(item);
      groups.set(item.folder, list);
    }
    return Array.from(groups.entries());
  }, [evidenceKnowledgeItems]);

  const reviewSummary = useMemo(() => summariseReview(session?.last_review ?? null), [session]);

  const selectedPlaybook = useMemo(
    () => playbooks.find((playbook) => playbook.id === selectedPlaybookId) ?? null,
    [playbooks, selectedPlaybookId]
  );

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
    setSession(null);
    setDraft("");
    setLastSubmittedDraft("");
    setError(null);
    setIsSending(false);
  }

  function handleDraftKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
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

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-brand">
          <div className="workspace-brand__mark">△</div>
          <div>
            <strong>三眼科技</strong>
            <span>SANYAN AI</span>
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
            <strong>三眼技术评审通用 Agent</strong>
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
                message.role === "assistant" ? "workspace-message--assistant" : "workspace-message--user"
              }`}
            >
              <div className="workspace-avatar">{message.role === "assistant" ? "◉" : "你"}</div>
              <div className="workspace-message__body">
                <div className="workspace-message__meta">
                  <strong>{message.role === "assistant" ? "三眼 Agent" : "你"}</strong>
                  <span>{message.timestamp}</span>
                </div>
                <p>{message.content}</p>
              </div>
            </article>
          ))}
        </div>

        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
        {session?.resume_available && !isSending ? (
          <p className="workspace-status">
            当前会话存在可恢复断点（{session.resume_reason ?? "unknown"}）。
            <button type="button" onClick={() => void handleResumeSession()}>
              继续执行
            </button>
          </p>
        ) : null}

        <div className="workspace-composer">
          <div className="workspace-skill-hints">
            <span>技能清单</span>
            <div className="workspace-skill-hints__list">
              {skills.map((skill) => (
                <button
                  key={skill.name}
                  type="button"
                  onClick={() =>
                    setDraft((current) =>
                      current.trim()
                        ? `${current}\n使用技能：${skill.name}`
                        : `使用技能：${skill.name}\n${skill.description}`
                    )
                  }
                >
                  {skill.name}
                </button>
              ))}
            </div>
          </div>
          <textarea
            rows={4}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleDraftKeyDown}
            placeholder="输入技术评审问题，也可以直接写“使用技能：xxx”，Agent 会基于当前项目空间和资料库持续多轮对话。"
          />
          <div className="workspace-composer__footer">
            <div className="workspace-composer__actions">
              <button type="button">上传文档</button>
              <button type="button">扫描风险</button>
              <button type="button">生成结论</button>
            </div>
            <div className="workspace-composer__submit">
              <label className="workspace-composer__control">
                <span>模式</span>
                <select value={mode} onChange={(event) => setMode(event.target.value as typeof mode)}>
                  <option value="quick">quick</option>
                  <option value="standard">standard</option>
                  <option value="strict">strict</option>
                </select>
              </label>
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
              <span>
                {selectedPlaybook?.name ?? "未选择技能包"} · {selectedProject?.name ?? "未选择项目"}
              </span>
            </div>
            <button type="button">⋯</button>
          </div>

          <div className="workspace-doc-tabs">
            <button type="button" className="workspace-doc-tabs__active">
              全部
            </button>
            <button type="button">文档 {knowledgeGroups.reduce((acc, [, items]) => acc + items.length, 0)}</button>
            <button type="button">图表 {playbookDetail?.rules.length ?? 0}</button>
            <button type="button">附件 {playbookDetail?.evidence.length ?? fallbackKnowledgeItems.length}</button>
          </div>

          <div className="workspace-doc-search">
            <input placeholder="搜索资料" value="" readOnly />
            <button type="button">☰</button>
          </div>

          <div className="workspace-doc-tree">
            {knowledgeGroups.map(([group, items]) => (
              <div key={group} className="workspace-doc-group">
                <div className="workspace-doc-group__title">
                  <span>▾</span>
                  <strong>{group}</strong>
                </div>
                {items.map((item) => (
                  <div key={item.id} className="workspace-doc-item">
                    <span className={`workspace-doc-item__icon workspace-doc-item__icon--${item.kind}`}>
                      {iconForKind(item.kind)}
                    </span>
                    <div className="workspace-doc-item__body">
                      <strong>{item.name}</strong>
                      <small>
                        {kindLabel[item.kind]} · {item.size}
                      </small>
                    </div>
                    <time>{item.updatedAt}</time>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <button type="button" className="workspace-upload">
            ＋ 上传资料
          </button>
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
            <button type="button">待确认</button>
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
