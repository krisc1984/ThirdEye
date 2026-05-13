"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { MarkdownMessage } from "@/components/MarkdownMessage";
import {
  generateReviewReport,
  getKnowledgeWorkspaceFileContent,
  listKnowledgeWorkspaceFiles,
  saveKnowledgeWorkspaceMarkdown
} from "@/lib/api";
import type { KnowledgeWorkspaceBinding, KnowledgeWorkspaceListing, PlaybookDetail, ReviewConversationSession } from "@/lib/api";

type ReviewReportWorkspaceProps = {
  session: ReviewConversationSession;
  playbook: PlaybookDetail;
  activeAgentName?: string | null;
  initialMarkdown: string;
  knowledgeBinding?: KnowledgeWorkspaceBinding | null;
  knowledgeListing?: KnowledgeWorkspaceListing | null;
  projectId?: string | null;
};

type ReportAssistantMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function ReviewReportWorkspace({
  session,
  playbook,
  activeAgentName,
  initialMarkdown,
  knowledgeBinding,
  knowledgeListing,
  projectId
}: ReviewReportWorkspaceProps) {
  const [markdown, setMarkdown] = useState(initialMarkdown);
  const [draftMarkdown, setDraftMarkdown] = useState<string | null>(null);
  const [assistantDraft, setAssistantDraft] = useState("");
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [assistantExecutionNote, setAssistantExecutionNote] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"edit" | "preview">("edit");
  const [expandedMessageIds, setExpandedMessageIds] = useState<string[]>([]);
  const [localKnowledgeListing, setLocalKnowledgeListing] = useState<KnowledgeWorkspaceListing | null>(knowledgeListing ?? null);
  const [isPending, startTransition] = useTransition();
  const [assistantMessages, setAssistantMessages] = useState<ReportAssistantMessage[]>([
    {
      id: "assistant-welcome",
      role: "assistant",
      content:
        "我会基于最新评审结论和关键会话，协助你整理 Markdown 格式评审报告。你可以让我补章节、润色措辞、压缩摘要或重写行动项。"
    }
  ]);

  const keyMessages = useMemo(
    () =>
      session.messages
        .filter((message) => message.role === "assistant" || message.role === "user")
        .slice(-8)
        .map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          created_at: message.created_at
        })),
    [session.messages]
  );

  const knowledgeItems = useMemo(() => {
    if (localKnowledgeListing?.items?.length) {
      return localKnowledgeListing.items.slice(0, 24).map((item) => ({
        id: item.relative_path,
        name: item.name,
        meta: item.is_dir ? "目录" : item.relative_path,
        relativePath: item.relative_path,
        isDir: item.is_dir
      }));
    }
    return playbook.evidence.slice(0, 12).map((item) => ({
      id: item.id,
      name: item.path.split(/[\\/]/).pop() || item.path,
      meta: item.summary,
      relativePath: null,
      isDir: false
    }));
  }, [localKnowledgeListing?.items, playbook.evidence]);

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

  function toggleMessageExpanded(messageId: string) {
    setExpandedMessageIds((current) =>
      current.includes(messageId) ? current.filter((item) => item !== messageId) : [...current, messageId]
    );
  }

  async function refreshKnowledgeListing() {
    if (!projectId && !knowledgeBinding?.effective_root_path) {
      return;
    }
    const listing = await listKnowledgeWorkspaceFiles({ project_id: projectId ?? null });
    setLocalKnowledgeListing(listing);
  }

  useEffect(() => {
    setLocalKnowledgeListing(knowledgeListing ?? null);
  }, [knowledgeListing]);

  useEffect(() => {
    if (!knowledgeBinding?.effective_root_path && !projectId) {
      return;
    }
    void refreshKnowledgeListing();
  }, [knowledgeBinding?.effective_root_path, projectId]);

  function handleAssistantSubmit() {
    const nextInput = assistantDraft.trim();
    if (!nextInput) return;
    setAssistantError(null);
    setAssistantExecutionNote(null);
    setSaveStatus(null);
    const userMessage: ReportAssistantMessage = { id: `user-${Date.now()}`, role: "user", content: nextInput };
    setAssistantMessages((current) => [...current, userMessage]);
    setAssistantDraft("");
    startTransition(async () => {
      try {
        const result = await generateReviewReport({
          session_id: session.id,
          playbook_id: playbook.metadata.id,
          markdown,
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
          setDraftMarkdown(result.suggested_markdown);
        }
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "报告助手调用失败。");
      }
    });
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

  function handleSaveMarkdown() {
    setAssistantError(null);
    setSaveStatus(null);
    const filename = `${playbook.metadata.name.replace(/[^\w\u4e00-\u9fa5-]+/g, "-")}-评审报告.md`;
    startTransition(async () => {
      try {
        const result = await saveKnowledgeWorkspaceMarkdown({
          project_id: projectId ?? null,
          filename,
          content: markdown
        });
        await refreshKnowledgeListing();
        setSaveStatus(`报告已保存到资料区：${result.uploaded_files[0] ?? filename}`);
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "保存报告失败。");
      }
    });
  }

  function handleOpenKnowledgeMarkdown(relativePath: string) {
    setAssistantError(null);
    setSaveStatus(null);
    startTransition(async () => {
      try {
        const result = await getKnowledgeWorkspaceFileContent({
          project_id: projectId ?? null,
          relative_path: relativePath
        });
        setMarkdown(result.content);
        setDraftMarkdown(null);
        setViewMode("edit");
        await refreshKnowledgeListing();
        setSaveStatus(
          result.truncated ? `已打开 ${result.relative_path}，内容过长，当前展示前 512KB。` : `已打开 ${result.relative_path}。`
        );
      } catch (caughtError) {
        setAssistantError(caughtError instanceof Error ? caughtError.message : "打开资料区 Markdown 失败。");
      }
    });
  }

  return (
    <section className="report-shell">
      <aside className="report-sidebar">
        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>资料区</strong>
              <span>{knowledgeBinding?.effective_root_path ?? "引用当前评审证据"}</span>
            </div>
          </div>
          <div className="report-reference-list">
            {knowledgeItems.length ? (
              knowledgeItems.map((item) => (
                <article key={item.id} className="report-reference-item">
                  {item.relativePath && !item.isDir && item.name.toLowerCase().endsWith(".md") ? (
                    <button
                      type="button"
                      className="report-reference-item__link"
                      onClick={() => handleOpenKnowledgeMarkdown(item.relativePath)}
                      disabled={isPending}
                    >
                      {item.name}
                    </button>
                  ) : (
                    <strong>{item.name}</strong>
                  )}
                  <small>{item.meta}</small>
                </article>
              ))
            ) : (
              <p className="workspace-empty">当前没有可展示的资料项。</p>
            )}
          </div>
        </section>
      </aside>

      <div className="report-main">
        <header className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>评审报告草稿</strong>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button">{activeAgentName?.trim() || "三眼Agent"}</button>
            <button type="button">{session.last_review?.overall_judgement ?? "待确认"}</button>
            <button type="button" onClick={handleSaveMarkdown} disabled={isPending}>
              {isPending ? "保存中..." : "保存报告"}
            </button>
          </div>
        </header>

        <section className="workspace-panel report-editor-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>Markdown 编辑区</strong>
              <span>基于最新评审结论自动生成，可继续手工修改</span>
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
      </div>

      <aside className="report-rightbar">
        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>关键会话</strong>
              <span>最新评审结论与关键过程摘录</span>
            </div>
          </div>
          <div className="report-conversation-list">
            {keyMessages.map((message) => (
              <article key={message.id} className="report-conversation-item">
                <button
                  type="button"
                  className="report-conversation-item__summary"
                  onClick={() => toggleMessageExpanded(message.id)}
                >
                  <div className="report-conversation-item__meta">
                    <strong>{message.role === "assistant" ? activeAgentName?.trim() || "三眼Agent" : "你"}</strong>
                    <span>{formatTime(message.created_at)}</span>
                  </div>
                  <span className="report-conversation-item__single-line">
                    {message.content.replace(/\s+/g, " ").trim() || "空消息"}
                  </span>
                </button>
                {expandedMessageIds.includes(message.id) ? <MarkdownMessage content={message.content} /> : null}
              </article>
            ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>Agent 助手</strong>
              <span>围绕报告草稿继续追问</span>
            </div>
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
              placeholder="例如：把这份报告改成适合发给管理层的摘要格式。"
            />
            <button type="button" onClick={handleAssistantSubmit} disabled={isPending || !assistantDraft.trim()}>
              {isPending ? "生成中..." : "发送"}
            </button>
          </div>
          {assistantExecutionNote ? <p className="workspace-status">{assistantExecutionNote}</p> : null}
          {saveStatus ? <p className="workspace-status">{saveStatus}</p> : null}
          {assistantError ? <p className="workspace-status workspace-status--error">{assistantError}</p> : null}
        </section>
      </aside>
    </section>
  );
}
