"use client";

import { useEffect, useMemo, useRef, useState, useTransition, type ChangeEvent } from "react";

import { MarkdownMessage } from "@/components/MarkdownMessage";
import {
  generateReviewReport,
  getKnowledgeWorkspaceDocxContent,
  getKnowledgeWorkspaceFileContent,
  listKnowledgeWorkspaceFiles,
  saveKnowledgeWorkspaceDocx,
  saveKnowledgeWorkspaceMarkdown,
  uploadKnowledgeWorkspaceFiles
} from "@/lib/api";
import type { KnowledgeWorkspaceBinding, KnowledgeWorkspaceListing, PlaybookDetail, ReviewConversationSession } from "@/lib/api";

type ReviewReportWorkspaceProps = {
  session: ReviewConversationSession;
  playbook: PlaybookDetail;
  activeAgentName?: string | null;
  initialMarkdown: string;
  preferredMode?: "auto" | "markdown" | "document";
  knowledgeBinding?: KnowledgeWorkspaceBinding | null;
  knowledgeListing?: KnowledgeWorkspaceListing | null;
  projectId?: string | null;
};

type ReportAssistantMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

type ReferenceFilter = "all" | "doc" | "image" | "link";

type ReferenceItem = {
  id: string;
  name: string;
  relativePath: string | null;
  summary: string;
  isDir: boolean;
  kind: ReferenceFilter;
  depth: number;
  updatedAt?: string | null;
};

type ReviewPoint = {
  id: string;
  sectionId: string;
  title: string;
  severity: "blocker" | "major" | "minor" | "nit";
  reviewComment: string;
  suggestion: string;
  validationText: string;
};

const SECTION_DEFINITIONS = [
  { id: "overview", title: "1. 项目概述" },
  { id: "requirements", title: "2. 功能需求" },
  { id: "interaction", title: "3. 交互设计" },
  { id: "technical", title: "4. 技术方案" }
] as const;

const QUICK_PROMPTS = [
  "分析文档整体质量",
  "检查逻辑结构是否完整",
  "识别潜在风险点",
  "生成评审总结"
];

function isWordDocument(name: string) {
  return /\.(doc|docx)$/i.test(name);
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatClock(value: Date) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(value);
}

function sanitizeFilenameSegment(value: string) {
  const normalized = value.replace(/[^\w\u4e00-\u9fa5-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return normalized || "评审报告";
}

function buildTimestampedReportFilename(playbookName: string, sessionCreatedAt: string) {
  const date = new Date(sessionCreatedAt);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  const second = String(date.getSeconds()).padStart(2, "0");
  return `${sanitizeFilenameSegment(playbookName)}-评审报告-${year}${month}${day}-${hour}${minute}${second}.md`;
}

function truncateText(value: string, maxLength = 72) {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return "待补充评审点";
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

function severityLabel(severity: ReviewPoint["severity"]) {
  switch (severity) {
    case "blocker":
      return "严重";
    case "major":
      return "中高";
    case "minor":
      return "一般";
    case "nit":
      return "轻微";
    default:
      return "一般";
  }
}

function classifyReferenceKind(name: string): ReferenceFilter {
  const lowerName = name.toLowerCase();
  if (/\.(png|jpg|jpeg|gif|webp|svg|bmp)$/.test(lowerName)) {
    return "image";
  }
  if (/\.(url|webloc|html)$/.test(lowerName)) {
    return "link";
  }
  return "doc";
}

function canPreviewReference(name: string) {
  return /\.(md|txt|json|ya?ml|csv|log|py|ts|tsx|js|jsx|css|html)$/i.test(name);
}

function resolveSectionId(input: string) {
  const text = input.toLowerCase();
  if (/(ui|ux|交互|页面|界面|体验|流程|视觉|易用|信息架构)/.test(text)) {
    return "interaction";
  }
  if (/(架构|技术|接口|性能|扩展|部署|安全|稳定|数据|并发|实现|模块|服务|方案)/.test(text)) {
    return "technical";
  }
  if (/(需求|用户|场景|流程|角色|功能|目标|价值|业务)/.test(text)) {
    return "requirements";
  }
  return "overview";
}

function buildFallbackPoints(session: ReviewConversationSession) {
  const review = session.last_review;
  const rawItems = [
    ...(review?.key_risks ?? []),
    ...(review?.suggested_changes ?? []),
    ...(review?.required_validation ?? [])
  ].filter(Boolean);

  return rawItems.slice(0, 6).map((item, index) => {
    const sectionId = SECTION_DEFINITIONS[index % SECTION_DEFINITIONS.length]?.id ?? "overview";
    return {
      id: `fallback-${index}`,
      sectionId,
      title: truncateText(item),
      severity: "minor" as const,
      reviewComment: item,
      suggestion: review?.suggested_changes[index] ?? "补充更明确的修改动作、负责人和验收口径。",
      validationText: review?.required_validation[index] ?? "补充验证结果。"
    };
  });
}

function buildReviewPoints(session: ReviewConversationSession, playbook: PlaybookDetail): ReviewPoint[] {
  const review = session.last_review;
  if (!review?.findings?.length) {
    return buildFallbackPoints(session);
  }

  return review.findings.map((finding, index) => {
    const rule = finding.rule_id ? playbook.rules.find((item) => item.id === finding.rule_id) : null;
    const title = rule?.name ?? truncateText(finding.problem, 44);
    const sectionId = resolveSectionId(
      [title, finding.problem, finding.impact, finding.suggested_change, rule?.category, rule?.applicability?.join(" ")]
        .filter(Boolean)
        .join(" ")
    );

    return {
      id: `${finding.rule_id ?? "finding"}-${index}`,
      sectionId,
      title,
      severity: finding.severity,
      reviewComment: [finding.problem, finding.impact].filter(Boolean).join(" "),
      suggestion: finding.suggested_change || "补充建议修改。",
      validationText: finding.required_validation.join("；") || "补充验证结果。"
    };
  });
}

function buildReviewMarkdown(playbook: PlaybookDetail, session: ReviewConversationSession, reviewPoints: ReviewPoint[]) {
  const review = session.last_review;
  const grouped = SECTION_DEFINITIONS.map((section) => ({
    ...section,
    items: reviewPoints.filter((item) => item.sectionId === section.id)
  })).filter((section) => section.items.length > 0);

  return [
    `# 设计文档评审`,
    "",
    `- 文档：${playbook.metadata.name}`,
    `- 会话：${session.id}`,
    `- 结论：${review?.overall_judgement ?? "待确认"}`,
    `- 更新时间：${new Date(session.updated_at).toLocaleString("zh-CN")}`,
    "",
    ...grouped.flatMap((section) => [
      `## ${section.title}`,
      "",
      ...section.items.flatMap((item, index) => [
        `### ${section.title.split(". ")[0]}.${index + 1} ${item.title}`,
        `- 严重度：${severityLabel(item.severity)}`,
        `- 评审意见：${item.reviewComment}`,
        `- 建议修改：${item.suggestion}`,
        `- 验证建议：${item.validationText}`,
        ""
      ])
    ])
  ].join("\n");
}

function buildWordDocumentDraft(playbook: PlaybookDetail, session: ReviewConversationSession, reviewPoints: ReviewPoint[]) {
  const review = session.last_review;
  const firstRisk = review?.key_risks?.[0] ?? session.latest_summary ?? "请在这里补充设计文档的背景、目标和核心范围。";
  const grouped = SECTION_DEFINITIONS.map((section) => ({
    ...section,
    items: reviewPoints.filter((item) => item.sectionId === section.id)
  })).filter((section) => section.items.length > 0);

  return [
    `${playbook.metadata.name} 评审稿`,
    "",
    "一、文档概述",
    firstRisk,
    "",
    "二、评审意见",
    ...grouped.flatMap((section) => [
      "",
      section.title,
      ...section.items.flatMap((item, index) => [
        `${section.title.split(". ")[0]}.${index + 1} ${item.title}`,
        `评审意见：${item.reviewComment}`,
        `建议修改：${item.suggestion}`,
        `验证建议：${item.validationText}`
      ])
    ]),
    "",
    "三、结论",
    review?.overall_judgement ?? "待确认"
  ].join("\n");
}

function buildReferenceItems(listing: KnowledgeWorkspaceListing | null, playbook: PlaybookDetail): ReferenceItem[] {
  if (listing?.items?.length) {
    return listing.items
      .slice()
      .sort((left, right) => {
        if (left.is_dir !== right.is_dir) {
          return left.is_dir ? -1 : 1;
        }
        return left.relative_path.localeCompare(right.relative_path, "zh-CN");
      })
      .map((item) => ({
        id: item.relative_path,
        name: item.name,
        relativePath: item.relative_path,
        summary: item.is_dir ? "文件夹" : item.relative_path,
        isDir: item.is_dir,
        kind: classifyReferenceKind(item.name),
        depth: item.relative_path.split(/[\\/]/).length - 1,
        updatedAt: item.updated_at
      }));
  }

  return playbook.evidence.slice(0, 20).map((item) => ({
    id: item.id,
    name: item.path.split(/[\\/]/).pop() || item.path,
    relativePath: null,
    summary: item.summary,
    isDir: false,
    kind: classifyReferenceKind(item.path),
    depth: Math.max(item.path.split(/[\\/]/).length - 2, 0),
    updatedAt: null
  }));
}

export function ReviewReportWorkspace({
  session,
  playbook,
  activeAgentName,
  initialMarkdown,
  preferredMode = "auto",
  knowledgeBinding,
  knowledgeListing,
  projectId
}: ReviewReportWorkspaceProps) {
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const [markdown, setMarkdown] = useState(initialMarkdown);
  const [wordDraft, setWordDraft] = useState(() => buildWordDocumentDraft(playbook, session, buildReviewPoints(session, playbook)));
  const [activeWordPath, setActiveWordPath] = useState<string | null>(null);
  const [draftMarkdown, setDraftMarkdown] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"edit" | "preview">("edit");
  const [reviewPoints, setReviewPoints] = useState<ReviewPoint[]>(() => buildReviewPoints(session, playbook));
  const [assistantDraft, setAssistantDraft] = useState("");
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [assistantExecutionNote, setAssistantExecutionNote] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [currentFilename, setCurrentFilename] = useState<string | null>(null);
  const [referenceQuery, setReferenceQuery] = useState("");
  const [referenceFilter, setReferenceFilter] = useState<ReferenceFilter>("all");
  const [selectedReferencePath, setSelectedReferencePath] = useState<string | null>(null);
  const [selectedReferenceTitle, setSelectedReferenceTitle] = useState<string | null>(null);
  const [referencePreview, setReferencePreview] = useState<string | null>(null);
  const [localKnowledgeListing, setLocalKnowledgeListing] = useState<KnowledgeWorkspaceListing | null>(knowledgeListing ?? null);
  const [isPending, startTransition] = useTransition();
  const [assistantMessages, setAssistantMessages] = useState<ReportAssistantMessage[]>([
    {
      id: "assistant-welcome",
      role: "assistant",
      content:
        "你好，我是 AI 评审助手。我可以帮你分析设计文档、提炼评审意见，并把修改建议整理成可直接落到文档里的内容。"
    }
  ]);

  useEffect(() => {
    const nextReviewPoints = buildReviewPoints(session, playbook);
    setReviewPoints(nextReviewPoints);
    setMarkdown(initialMarkdown);
    setWordDraft(buildWordDocumentDraft(playbook, session, nextReviewPoints));
    setDraftMarkdown(null);
    setViewMode("edit");
    setCurrentFilename(null);
  }, [initialMarkdown, playbook, session]);

  useEffect(() => {
    setLocalKnowledgeListing(knowledgeListing ?? null);
  }, [knowledgeListing]);

  const referenceItems = useMemo(() => buildReferenceItems(localKnowledgeListing, playbook), [localKnowledgeListing, playbook]);

  const filteredReferenceItems = useMemo(() => {
    return referenceItems.filter((item) => {
      if (referenceFilter !== "all" && item.kind !== referenceFilter) {
        return false;
      }
      if (!referenceQuery.trim()) {
        return true;
      }
      const keyword = referenceQuery.trim().toLowerCase();
      return `${item.name} ${item.summary}`.toLowerCase().includes(keyword);
    });
  }, [referenceFilter, referenceItems, referenceQuery]);

  const hasWordAttachment = useMemo(
    () => referenceItems.some((item) => !item.isDir && isWordDocument(item.name)),
    [referenceItems]
  );
  const firstWordAttachment = useMemo(
    () => referenceItems.find((item) => !item.isDir && item.relativePath && isWordDocument(item.name)) ?? null,
    [referenceItems]
  );
  const isDocumentMode = preferredMode === "document" ? true : preferredMode === "markdown" ? false : hasWordAttachment;

  const reviewSections = useMemo(
    () =>
      SECTION_DEFINITIONS.map((section) => ({
        ...section,
        items: reviewPoints.filter((item) => item.sectionId === section.id)
      })).filter((section) => section.items.length > 0),
    [reviewPoints]
  );

  const reviewStats = useMemo(() => {
    return reviewPoints.reduce(
      (summary, item) => {
        summary.total += 1;
        if (item.severity === "blocker" || item.severity === "major") {
          summary.high += 1;
        } else if (item.severity === "minor") {
          summary.medium += 1;
        } else {
          summary.low += 1;
        }
        return summary;
      },
      { total: 0, high: 0, medium: 0, low: 0 }
    );
  }, [reviewPoints]);

  const computedMarkdown = useMemo(
    () => buildReviewMarkdown(playbook, session, reviewPoints),
    [playbook, reviewPoints, session]
  );

  const computedWordMarkdown = useMemo(() => {
    const review = session.last_review;
    return [
      `# ${playbook.metadata.name} 评审稿`,
      "",
      `- 会话：${session.id}`,
      `- 结论：${review?.overall_judgement ?? "待确认"}`,
      `- 更新时间：${new Date(session.updated_at).toLocaleString("zh-CN")}`,
      "",
      wordDraft
    ].join("\n");
  }, [playbook.metadata.name, session.id, session.last_review, session.updated_at, wordDraft]);

  const diffPreview = useMemo(() => {
    if (!draftMarkdown || draftMarkdown === markdown) {
      return null;
    }
    const currentLines = markdown.split("\n");
    const nextLines = draftMarkdown.split("\n");
    const maxLines = Math.max(currentLines.length, nextLines.length);
    const rows: Array<{ kind: "added" | "removed" | "same"; text: string }> = [];
    for (let index = 0; index < maxLines; index += 1) {
      const current = currentLines[index];
      const next = nextLines[index];
      if (current === next) {
        if (current !== undefined) {
          rows.push({ kind: "same", text: current });
        }
        continue;
      }
      if (current !== undefined) {
        rows.push({ kind: "removed", text: current });
      }
      if (next !== undefined) {
        rows.push({ kind: "added", text: next });
      }
    }
    return rows.slice(0, 160);
  }, [draftMarkdown, markdown]);

  async function refreshKnowledgeListing() {
    if (!projectId && !knowledgeBinding?.effective_root_path) {
      return;
    }
    const listing = await listKnowledgeWorkspaceFiles({ project_id: projectId ?? null });
    setLocalKnowledgeListing(listing);
  }

  useEffect(() => {
    if (!knowledgeBinding?.effective_root_path && !projectId) {
      return;
    }
    void refreshKnowledgeListing();
  }, [knowledgeBinding?.effective_root_path, projectId]);

  useEffect(() => {
    if (!isDocumentMode || !firstWordAttachment?.relativePath) {
      return;
    }
    if (activeWordPath === firstWordAttachment.relativePath) {
      return;
    }

    setAssistantError(null);
    startTransition(async () => {
      try {
        const result = await getKnowledgeWorkspaceDocxContent({
          project_id: projectId ?? null,
          relative_path: firstWordAttachment.relativePath as string
        });
        setWordDraft(result.content || buildWordDocumentDraft(playbook, session, reviewPoints));
        setActiveWordPath(result.relative_path);
        setCurrentFilename(result.relative_path.split(/[\\/]/).pop() ?? result.relative_path);
        if (result.truncated) {
          setSaveStatus(`已读取 ${result.relative_path}，内容过长，当前展示截断内容。`);
        }
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "读取 Word 文档失败。");
      }
    });
  }, [activeWordPath, firstWordAttachment?.relativePath, isDocumentMode, playbook, projectId, reviewPoints, session]);

  function updateReviewPoint(id: string, field: "reviewComment" | "suggestion", value: string) {
    setReviewPoints((current) => current.map((item) => (item.id === id ? { ...item, [field]: value } : item)));
    setSaveStatus(null);
  }

  function runAssistantPrompt(message: string) {
    const nextInput = message.trim();
    if (!nextInput) return;

    setAssistantDraft("");
    setAssistantError(null);
    setAssistantExecutionNote(null);
    setSaveStatus(null);

    const userMessage: ReportAssistantMessage = { id: `user-${Date.now()}`, role: "user", content: nextInput };
    setAssistantMessages((current) => [...current, userMessage]);

    startTransition(async () => {
      try {
        const result = await generateReviewReport({
          session_id: session.id,
          playbook_id: playbook.metadata.id,
          markdown: isDocumentMode ? computedWordMarkdown : markdown,
          instruction: nextInput
        });
        setAssistantMessages((current) => [
          ...current,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: result.reply
          }
        ]);
        setAssistantExecutionNote(result.execution_note ?? null);
        if (result.suggested_markdown.trim()) {
          if (isDocumentMode) {
            setWordDraft(result.suggested_markdown);
            setAssistantExecutionNote("已将 Agent 生成内容更新到 Word 编辑区。");
          } else {
            setDraftMarkdown(result.suggested_markdown);
          }
        }
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "报告助手调用失败。");
      }
    });
  }

  function handleSaveMarkdown() {
    setAssistantError(null);
    setSaveStatus(null);
    const filename = currentFilename ?? buildTimestampedReportFilename(playbook.metadata.name, session.created_at);

    startTransition(async () => {
      try {
        const result = isDocumentMode
          ? await saveKnowledgeWorkspaceDocx({
              project_id: projectId ?? null,
              filename: filename.toLowerCase().endsWith(".docx") ? filename : filename.replace(/\.md$/i, "") + ".docx",
              content: wordDraft,
              source_relative_path: activeWordPath
            })
          : await saveKnowledgeWorkspaceMarkdown({
              project_id: projectId ?? null,
              filename,
              content: markdown
            });
        const savedFilename = result.uploaded_files[0] ?? filename;
        setCurrentFilename(savedFilename);
        if (isDocumentMode) {
          setActiveWordPath(savedFilename);
        }
        await refreshKnowledgeListing();
        setSaveStatus(`评审文档已保存到资料区：${savedFilename}`);
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "保存报告失败。");
      }
    });
  }

  function handleOpenReference(item: ReferenceItem) {
    if (!item.relativePath || item.isDir || (!canPreviewReference(item.name) && !isWordDocument(item.name))) {
      return;
    }

    setAssistantError(null);
    setSelectedReferencePath(item.relativePath);
    setSelectedReferenceTitle(item.name);

    startTransition(async () => {
      try {
        const result = isWordDocument(item.name)
          ? await getKnowledgeWorkspaceDocxContent({
              project_id: projectId ?? null,
              relative_path: item.relativePath as string
            })
          : await getKnowledgeWorkspaceFileContent({
              project_id: projectId ?? null,
              relative_path: item.relativePath as string
            });
        setReferencePreview(result.content);
        if (isWordDocument(item.name)) {
          setWordDraft(result.content || wordDraft);
          setActiveWordPath(result.relative_path);
          setCurrentFilename(item.name);
        }
        setSaveStatus(
          result.truncated ? `已打开 ${result.relative_path}，当前预览为截断内容。` : `已打开 ${result.relative_path}。`
        );
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "打开资料预览失败。");
      }
    });
  }

  function handleUploadClick() {
    uploadInputRef.current?.click();
  }

  function handleAcceptSuggestedMarkdown() {
    if (!draftMarkdown) return;
    setMarkdown(draftMarkdown);
    setDraftMarkdown(null);
    setSaveStatus("已接受 Agent 生成的改写结果。");
  }

  function handleDiscardSuggestedMarkdown() {
    setDraftMarkdown(null);
    setSaveStatus("已丢弃本次改写结果。");
  }

  function handleUploadFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;

    setAssistantError(null);
    setSaveStatus(null);

    startTransition(async () => {
      try {
        await uploadKnowledgeWorkspaceFiles({
          project_id: projectId ?? null,
          files
        });
        await refreshKnowledgeListing();
        setSaveStatus(`已上传 ${files.length} 个资料文件。`);
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "上传资料失败。");
      } finally {
        if (uploadInputRef.current) {
          uploadInputRef.current.value = "";
        }
      }
    });
  }

  return (
    <section className="report-shell report-shell--document-review">
      <aside className="report-sidebar">
        <section className="workspace-panel report-panel report-panel--sticky">
          <div className="report-panel__block">
            <div className="workspace-panel__header">
              <div>
                <strong>资料区</strong>
                <span>{knowledgeBinding?.effective_root_path ?? "当前项目资料"}</span>
              </div>
              <span className="report-panel__dots">••</span>
            </div>
            <button type="button" className="report-upload-button" onClick={handleUploadClick} disabled={isPending}>
              + 上传资料
            </button>
            <input ref={uploadInputRef} hidden type="file" multiple onChange={handleUploadFiles} />
            <div className="report-searchbar">
              <input
                value={referenceQuery}
                onChange={(event) => setReferenceQuery(event.target.value)}
                placeholder="搜索文件或文件夹"
              />
            </div>
            <div className="report-filter-tabs">
              {[
                ["all", "全部"],
                ["doc", "文档"],
                ["image", "图片"],
                ["link", "链接"]
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={referenceFilter === value ? "report-filter-tab report-filter-tab--active" : "report-filter-tab"}
                  onClick={() => setReferenceFilter(value as ReferenceFilter)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="report-file-tree">
            {filteredReferenceItems.length ? (
              filteredReferenceItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled={!item.relativePath || item.isDir || (!canPreviewReference(item.name) && !isWordDocument(item.name)) || isPending}
                  className={
                    selectedReferencePath === item.relativePath
                      ? "report-file-row report-file-row--active"
                      : "report-file-row"
                  }
                  onClick={() => handleOpenReference(item)}
                  title={item.summary}
                >
                  <span className="report-file-row__indent" style={{ width: `${item.depth * 12 + 8}px` }} />
                  <span className="report-file-row__icon">{item.isDir ? "▾" : item.kind === "image" ? "◫" : "▣"}</span>
                  <span className="report-file-row__label">{item.name}</span>
                </button>
              ))
            ) : (
              <p className="workspace-empty">没有匹配的资料项。</p>
            )}
          </div>

          <div className="report-storage-note">
            <span>资料项 {referenceItems.length}</span>
            <span>{projectId ? "项目知识库已绑定" : "当前使用评审证据集"}</span>
          </div>
        </section>

        {referencePreview ? (
          <section className="workspace-panel report-preview-card">
            <div className="workspace-panel__header">
              <div>
                <strong>{selectedReferenceTitle ?? "资料预览"}</strong>
                <span>{selectedReferencePath ?? "只读预览"}</span>
              </div>
            </div>
            <div className="report-preview-card__body">
              <pre>{referencePreview}</pre>
            </div>
          </section>
        ) : null}
      </aside>

      <div className="report-main">
        <header className="workspace-topbar report-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <div>
              <strong>{currentFilename ?? `${playbook.metadata.name}.md`}</strong>
              <span>自动保存草稿 {formatClock(new Date(session.updated_at))}</span>
            </div>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button">全屏</button>
            <button type="button" onClick={handleSaveMarkdown} disabled={isPending}>
              导出评审报告
            </button>
            <button type="button">评审视图：按章节</button>
          </div>
        </header>

        {isDocumentMode ? (
          <section className="workspace-panel document-review-panel">
            <div className="document-review-toolbar">
              <div className="document-review-toolbar__group">
                <button type="button" title="撤销">↶</button>
                <button type="button" title="重做">↷</button>
              </div>
              <div className="document-review-toolbar__group document-review-toolbar__group--wide">
                <select aria-label="段落样式" defaultValue="正文">
                  <option>正文</option>
                  <option>标题 1</option>
                  <option>标题 2</option>
                  <option>引用</option>
                </select>
                <select aria-label="字号" defaultValue="12">
                  <option>10</option>
                  <option>11</option>
                  <option>12</option>
                  <option>14</option>
                  <option>16</option>
                </select>
              </div>
              <div className="document-review-toolbar__group">
                <button type="button" title="加粗">B</button>
                <button type="button" title="斜体">I</button>
                <button type="button" title="下划线">U</button>
              </div>
              <div className="document-review-toolbar__status">
                <span>{preferredMode === "document" ? "文档编辑" : "Word 附件"}</span>
                <span>{wordDraft.length} 字</span>
              </div>
            </div>

            <div className="word-editor-stage">
              <div className="word-editor-ruler">
                {Array.from({ length: 12 }).map((_, index) => (
                  <span key={index}>{index + 1}</span>
                ))}
              </div>
              <div className="word-editor-workbench">
                <article className="word-page">
                  <header className="word-page__header">
                    <span>{playbook.metadata.name}</span>
                    <span>{formatClock(new Date(session.updated_at))}</span>
                  </header>
                  <textarea
                    className="word-page__editor"
                    value={wordDraft}
                    onChange={(event) => setWordDraft(event.target.value)}
                    spellCheck={false}
                  />
                  <footer className="word-page__footer">
                    <span>第 1 页</span>
                    <span>评审稿</span>
                  </footer>
                </article>

                <aside className="word-review-margin">
                  <div className="word-review-margin__summary">
                    <strong>批注</strong>
                    <span>{reviewStats.total} 条</span>
                  </div>
                  {reviewPoints.map((item, index) => (
                    <article key={item.id} className="word-comment">
                      <div className="word-comment__header">
                        <strong>{index + 1}. {item.title}</strong>
                        <span className={`document-review-severity document-review-severity--${item.severity}`}>
                          {severityLabel(item.severity)}
                        </span>
                      </div>
                      <label className="word-comment__field">
                        <span>评审意见</span>
                        <textarea
                          rows={3}
                          value={item.reviewComment}
                          onChange={(event) => updateReviewPoint(item.id, "reviewComment", event.target.value)}
                        />
                      </label>
                      <label className="word-comment__field">
                        <span>建议修改</span>
                        <textarea
                          rows={3}
                          value={item.suggestion}
                          onChange={(event) => updateReviewPoint(item.id, "suggestion", event.target.value)}
                        />
                      </label>
                    </article>
                  ))}
                </aside>
              </div>
            </div>
          </section>
        ) : (
          <section className="workspace-panel report-editor-panel">
            <div className="workspace-panel__header">
              <div>
                <strong>Markdown 编辑区</strong>
                <span>
                  {preferredMode === "markdown"
                    ? "当前为直达 Markdown 编辑模式。"
                    : "当前没有 Word 附件，保留原始报告编辑模式。"}
                </span>
              </div>
              <div className="report-mode-toggle">
                <button
                  type="button"
                  className={viewMode === "edit" ? "report-mode-toggle__button report-mode-toggle__button--active" : "report-mode-toggle__button"}
                  onClick={() => setViewMode("edit")}
                >
                  编辑
                </button>
                <button
                  type="button"
                  className={
                    viewMode === "preview" ? "report-mode-toggle__button report-mode-toggle__button--active" : "report-mode-toggle__button"
                  }
                  onClick={() => setViewMode("preview")}
                >
                  预览
                </button>
              </div>
            </div>

            <div className="report-editor-grid report-editor-grid--single">
              {viewMode === "edit" ? (
                <textarea
                  className="report-markdown-editor"
                  value={markdown}
                  onChange={(event) => setMarkdown(event.target.value)}
                  spellCheck={false}
                />
              ) : (
                <div className="report-preview-panel">
                  <div className="report-preview-panel__header">
                    <strong>预览</strong>
                    <span>{markdown.length} 字符</span>
                  </div>
                  <MarkdownMessage content={markdown} />
                </div>
              )}
            </div>

            {diffPreview ? (
              <div className="report-diff-panel">
                <div className="workspace-panel__header">
                  <div>
                    <strong>改写差异预览</strong>
                    <span>先确认再应用到编辑区</span>
                  </div>
                  <div className="report-diff-panel__actions">
                    <button type="button" onClick={handleAcceptSuggestedMarkdown}>
                      接受改写
                    </button>
                    <button type="button" onClick={handleDiscardSuggestedMarkdown}>
                      丢弃改写
                    </button>
                  </div>
                </div>
                <div className="report-diff-list">
                  {diffPreview.map((row, index) => (
                    <pre key={`${row.kind}-${index}`} className={`report-diff-row report-diff-row--${row.kind}`}>
                      {row.kind === "added" ? "+ " : row.kind === "removed" ? "- " : "  "}
                      {row.text}
                    </pre>
                  ))}
                </div>
              </div>
            ) : null}
          </section>
        )}
      </div>

      <aside className="report-rightbar">
        <section className="workspace-panel report-panel report-panel--sticky">
          <div className="workspace-panel__header">
            <div>
              <strong>AI 对话助手</strong>
              <span>{activeAgentName?.trim() || "三眼Agent"}</span>
            </div>
            <span className="report-assistant-badge">✦</span>
          </div>

          <div className="report-assistant-hero">
            <div className="report-assistant-hero__icon">🤖</div>
            <p>你好！我是 AI 助手，可以帮你分析文档内容、提炼评审建议并协助修改意见。</p>
          </div>

          <div className="report-assistant-shortcuts">
            {QUICK_PROMPTS.map((prompt) => (
              <button key={prompt} type="button" onClick={() => runAssistantPrompt(prompt)} disabled={isPending}>
                <span>{prompt}</span>
                <span>→</span>
              </button>
            ))}
          </div>

          <div className="report-assistant-thread">
            {assistantMessages.map((message) => (
              <article
                key={message.id}
                className={`report-assistant-message ${
                  message.role === "assistant" ? "report-assistant-message--assistant" : "report-assistant-message--user"
                }`}
              >
                <strong>{message.role === "assistant" ? activeAgentName?.trim() || "三眼Agent" : "你"}</strong>
                <MarkdownMessage content={message.content} />
              </article>
            ))}
          </div>

          <div className="report-assistant-composer">
            <textarea
              rows={4}
              value={assistantDraft}
              onChange={(event) => setAssistantDraft(event.target.value)}
              placeholder="输入问题，AI 助手为你解答..."
            />
            <div className="report-assistant-composer__footer">
              <span>0/500</span>
              <button type="button" onClick={() => runAssistantPrompt(assistantDraft)} disabled={isPending || !assistantDraft.trim()}>
                {isPending ? "生成中..." : "发送"}
              </button>
            </div>
          </div>

          {assistantExecutionNote ? <p className="workspace-status">{assistantExecutionNote}</p> : null}
          {saveStatus ? <p className="workspace-status">{saveStatus}</p> : null}
          {assistantError ? <p className="workspace-status workspace-status--error">{assistantError}</p> : null}
        </section>
      </aside>
    </section>
  );
}
