"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";

import type { BusinessAgentConfig } from "@/lib/api";
import { activateBusinessAgent, createBusinessAgent, updateBusinessAgent } from "@/lib/api";

type BusinessAgentSettingsProps = {
  initialAgents: BusinessAgentConfig[];
};

type FormState = {
  id: string;
  name: string;
  description: string;
  category: string;
  system_prompt: string;
};

const initialForm: FormState = {
  id: "",
  name: "",
  description: "",
  category: "review",
  system_prompt: ""
};

const featureChips = [
  { label: "业务 Agents", tone: "blue" },
  { label: "系统提示词", tone: "orange" },
  { label: "单一生效项", tone: "green" }
] as const;

function buildFormFromAgent(agent: BusinessAgentConfig): FormState {
  return {
    id: agent.id,
    name: agent.name,
    description: agent.description,
    category: agent.category,
    system_prompt: agent.system_prompt
  };
}

export function BusinessAgentSettings({ initialAgents }: BusinessAgentSettingsProps) {
  const [agents, setAgents] = useState(initialAgents);
  const [selectedAgentId, setSelectedAgentId] = useState(initialAgents[0]?.id ?? "");
  const [form, setForm] = useState<FormState>(() => (initialAgents[0] ? buildFormFromAgent(initialAgents[0]) : initialForm));
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId]
  );

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.is_default || agent.status === "active") ?? agents[0] ?? null,
    [agents]
  );

  const agentStats = useMemo(
    () => ({
      total: agents.length,
      active: agents.filter((agent) => agent.status === "active").length,
      categories: new Set(agents.map((agent) => agent.category)).size
    }),
    [agents]
  );

  function updateField<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function syncAgents(nextAgent: BusinessAgentConfig) {
    setAgents((current) => {
      const others = current.filter((item) => item.id !== nextAgent.id);
      const nextList = [nextAgent, ...others];
      if (nextAgent.is_default || nextAgent.status === "active") {
        return nextList.map((item) =>
          item.id === nextAgent.id
            ? item
            : {
                ...item,
                is_default: false,
                status: "draft"
              }
        );
      }
      return nextList;
    });
    setSelectedAgentId(nextAgent.id);
    setForm(buildFormFromAgent(nextAgent));
  }

  function handleSelectAgent(agent: BusinessAgentConfig) {
    setSelectedAgentId(agent.id);
    setForm(buildFormFromAgent(agent));
    setError(null);
    setStatusMessage(null);
  }

  function handleSave() {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const payload: BusinessAgentConfig = {
          id: form.id.trim(),
          name: form.name.trim(),
          description: form.description.trim(),
          category: form.category.trim(),
          system_prompt: form.system_prompt.trim(),
          status: selectedAgent?.status === "active" ? "active" : "draft",
          is_default: selectedAgent?.is_default ?? false
        };
        const exists = agents.some((agent) => agent.id === payload.id);
        const saved = exists ? await updateBusinessAgent(payload.id, payload) : await createBusinessAgent(payload);
        syncAgents(saved);
        setStatusMessage(exists ? "业务 Agent 已更新。" : "业务 Agent 已创建。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "保存业务 Agent 失败。");
      }
    });
  }

  function handleActivate(agentId: string) {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const activated = await activateBusinessAgent(agentId);
        setAgents((current) =>
          current.map((item) =>
            item.id === activated.id
              ? activated
              : {
                  ...item,
                  is_default: false,
                  status: "draft"
                }
          )
        );
        if (selectedAgentId === agentId) {
          setForm((current) => ({ ...current }));
        }
        setStatusMessage(`当前生效智能体已切换为「${activated.name}」。`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "切换当前生效智能体失败。");
      }
    });
  }

  return (
    <section className="settings-workspace">
      <aside className="settings-workspace__sidebar">
        <section className="workspace-panel settings-hero-card">
          <div className="workspace-brand">
            <div className="workspace-brand__mark">🤖</div>
            <div>
              <strong>智能体中心</strong>
              <span>Business Agent Control</span>
            </div>
          </div>
          <div className="settings-hero-card__body">
            <p className="settings-hero-card__eyebrow">AGENT CONFIG</p>
            <h1>集中维护业务智能体的系统提示词与当前生效项</h1>
            <p>这里管理独立的业务 agents 配置。后续新增测试评审、需求评审、代码评审等智能体时，直接在这里编辑和切换。</p>
          </div>
          <div className="settings-chip-row">
            {featureChips.map((chip) => (
              <span key={chip.label} className={`settings-chip settings-chip--${chip.tone}`}>
                {chip.label}
              </span>
            ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>智能体概况</strong>
              <span>当前共 {agentStats.total} 个业务 Agent</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>总数</span>
              <strong>{agentStats.total}</strong>
            </article>
            <article className="settings-stat-card">
              <span>生效中</span>
              <strong>{agentStats.active}</strong>
            </article>
            <article className="settings-stat-card">
              <span>分类</span>
              <strong>{agentStats.categories}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>已配置 Agents</strong>
              <span>选择、编辑或切换当前生效项</span>
            </div>
          </div>
          <div className="settings-provider-list">
            {agents.map((agent) => {
              const isSelected = agent.id === selectedAgentId;
              return (
                <article
                  key={agent.id}
                  className={`settings-provider-card ${isSelected ? "settings-provider-card--active" : ""}`}
                >
                  <div className="settings-provider-card__head">
                    <div>
                      <strong>{agent.name}</strong>
                      <span>{agent.id}</span>
                    </div>
                    <em>{agent.is_default ? "已生效" : "草稿"}</em>
                  </div>
                  <div className="settings-provider-card__meta">
                    <span>{agent.category}</span>
                    <span>{agent.status}</span>
                  </div>
                  <p className="settings-agent-card__description">{agent.description || "未填写描述。"}</p>
                  <div className="settings-provider-card__actions">
                    <button type="button" onClick={() => handleSelectAgent(agent)}>
                      编辑配置
                    </button>
                    {agent.id === "code-review-agent" ? (
                      <Link className="settings-provider-card__link" href="/review/code">
                        进入代码评审
                      </Link>
                    ) : null}
                    <button type="button" onClick={() => handleActivate(agent.id)} disabled={isPending || agent.is_default}>
                      {agent.is_default ? "当前生效" : "设为生效"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </aside>

      <div className="settings-workspace__main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>业务 Agent 配置台</strong>
          </div>
          <div className="settings-topbar__note">
            <span>系统提示词保存后立即持久化</span>
          </div>
        </section>

        <section className="workspace-panel settings-form-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>配置编辑区</strong>
              <span>维护业务 Agent 元数据与系统提示词</span>
            </div>
          </div>

          <form className="settings-form-grid">
            <label className="settings-field">
              <span>Agent ID</span>
              <input value={form.id} onChange={(event) => updateField("id", event.target.value)} placeholder="code-review-agent" />
            </label>

            <label className="settings-field">
              <span>显示名称</span>
              <input value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="代码评审 Agent" />
            </label>

            <label className="settings-field">
              <span>分类</span>
              <input value={form.category} onChange={(event) => updateField("category", event.target.value)} placeholder="engineering" />
            </label>

            <label className="settings-field">
              <span>状态</span>
              <input value={selectedAgent?.is_default ? "active" : "draft"} readOnly />
            </label>

            <label className="settings-field settings-field--full">
              <span>描述</span>
              <input
                value={form.description}
                onChange={(event) => updateField("description", event.target.value)}
                placeholder="说明这个业务 Agent 用于什么场景。"
              />
            </label>

            <label className="settings-field settings-field--full">
              <span>系统提示词</span>
              <textarea
                value={form.system_prompt}
                onChange={(event) => updateField("system_prompt", event.target.value)}
                placeholder="输入该业务 Agent 的 system prompt。"
                rows={16}
              />
            </label>

            <div className="settings-form-actions settings-field--full">
              <button
                type="button"
                className="settings-cta settings-cta--primary"
                disabled={isPending || !form.id.trim() || !form.name.trim() || !form.category.trim() || !form.system_prompt.trim()}
                onClick={handleSave}
              >
                {isPending ? "保存中..." : "保存配置"}
              </button>

              <button
                type="button"
                className="settings-cta settings-cta--secondary"
                disabled={isPending || !selectedAgentId}
                onClick={() => selectedAgent && handleActivate(selectedAgent.id)}
              >
                {selectedAgent?.is_default ? "当前已生效" : "设为当前生效"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <aside className="settings-workspace__right">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>当前生效智能体</strong>
              <span>{activeAgent?.name ?? "未配置"}</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{activeAgent?.name ?? "等待配置业务 Agent"}</h3>
            <p>{activeAgent?.description ?? "从左侧选择一个业务 Agent 并设置为当前生效项。"}</p>
            <div className="settings-focus__tags">
              <span>{activeAgent?.id ?? "agent-id"}</span>
              <span>{activeAgent?.category ?? "category"}</span>
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>提示词预览</strong>
              <span>当前生效智能体的 system prompt</span>
            </div>
          </div>
          <div className="settings-response-block settings-response-block--prompt">
            <span>System Prompt</span>
            <code>{activeAgent?.system_prompt ?? "暂无提示词。"}</code>
          </div>
        </section>

        {statusMessage ? <p className="workspace-status workspace-status--success">{statusMessage}</p> : null}
        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </aside>
    </section>
  );
}
