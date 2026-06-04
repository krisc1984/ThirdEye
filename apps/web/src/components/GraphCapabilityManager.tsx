"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";

import type {
  GraphCapabilityDefinition,
  GraphCapabilitySourceDescriptor,
  ModelProviderConfig,
} from "@/lib/api";
import {
  createGraphCapability,
  deleteGraphCapability,
  draftGraphCapability,
  updateGraphCapability,
} from "@/lib/api";

type GraphCapabilityManagerProps = {
  initialCapabilities: GraphCapabilityDefinition[];
  providers: ModelProviderConfig[];
  sources: GraphCapabilitySourceDescriptor[];
};

type CapabilityKind = GraphCapabilityDefinition["kind"];
type CapabilitySourceType = GraphCapabilitySourceDescriptor["source_type"];

type FormState = {
  id: string;
  name: string;
  kind: CapabilityKind;
  action: string;
  description: string;
  enabled: boolean;
  provider_id: string;
  source_type: CapabilitySourceType | "";
  source_id: string;
  config: string;
  input_schema: string;
  output_schema: string;
  retry_max_attempts: number;
  retry_backoff_seconds: number;
  retry_on: string;
  created_at: string;
};

const KIND_LABELS: Record<CapabilityKind, string> = {
  tool: "工具",
  skill: "技能",
  agent: "代理",
  service: "服务",
};

function prettyJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

function buildFormFromCapability(
  capability: GraphCapabilityDefinition,
  providerId = "",
): FormState {
  return {
    id: capability.id,
    name: capability.name,
    kind: capability.kind,
    action: capability.action,
    description: capability.description,
    enabled: capability.enabled,
    provider_id: providerId,
    source_type: capability.source?.source_type ?? "",
    source_id: capability.source?.source_id ?? "",
    config: prettyJson(capability.config),
    input_schema: prettyJson(capability.input_schema),
    output_schema: prettyJson(capability.output_schema),
    retry_max_attempts: capability.retry_policy.max_attempts,
    retry_backoff_seconds: capability.retry_policy.backoff_seconds,
    retry_on: capability.retry_policy.retry_on.join(", "),
    created_at: capability.created_at,
  };
}

function createEmptyForm(providerId = ""): FormState {
  return {
    id: "",
    name: "",
    kind: "tool",
    action: "",
    description: "",
    enabled: true,
    provider_id: providerId,
    source_type: "",
    source_id: "",
    config: "{}",
    input_schema: "{\n  \"type\": \"object\",\n  \"properties\": {}\n}",
    output_schema: "{\n  \"type\": \"object\",\n  \"properties\": {}\n}",
    retry_max_attempts: 1,
    retry_backoff_seconds: 0,
    retry_on: "",
    created_at: new Date().toISOString(),
  };
}

function parseJsonField(label: string, value: string) {
  try {
    const parsed = JSON.parse(value || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${label} 必须是 JSON 对象`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message.includes("必须是 JSON 对象")) {
      throw error;
    }
    throw new Error(`${label} 不是合法 JSON`);
  }
}

function capabilityToPayload(
  form: FormState,
  source: GraphCapabilitySourceDescriptor | null,
): GraphCapabilityDefinition {
  return {
    id: form.id.trim(),
    name: form.name.trim(),
    kind: form.kind,
    action: form.action.trim(),
    description: form.description.trim(),
    enabled: form.enabled,
    config: parseJsonField("配置", form.config),
    input_schema: parseJsonField("输入 Schema", form.input_schema),
    output_schema: parseJsonField("输出 Schema", form.output_schema),
    retry_policy: {
      max_attempts: form.retry_max_attempts,
      backoff_seconds: form.retry_backoff_seconds,
      retry_on: form.retry_on
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    },
    source: form.source_type && form.source_id
      ? {
          source_type: form.source_type,
          source_id: form.source_id,
          source_name: source?.name ?? "",
          metadata: source?.metadata ?? {},
        }
      : null,
    created_at: form.created_at,
  };
}

export function GraphCapabilityManager({
  initialCapabilities,
  providers,
  sources,
}: GraphCapabilityManagerProps) {
  const initialProviderId = providers[0]?.id ?? "";
  const [capabilities, setCapabilities] = useState(initialCapabilities);
  const [selectedCapabilityId, setSelectedCapabilityId] = useState(initialCapabilities[0]?.id ?? "");
  const [form, setForm] = useState<FormState>(() =>
    initialCapabilities[0]
      ? buildFormFromCapability(initialCapabilities[0], initialProviderId)
      : createEmptyForm(initialProviderId),
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const selectedCapability = useMemo(
    () => capabilities.find((item) => item.id === selectedCapabilityId) ?? null,
    [capabilities, selectedCapabilityId],
  );

  const sourceGroups = useMemo(
    () => ({
      skill: sources.filter((item) => item.source_type === "skill"),
      agent: sources.filter((item) => item.source_type === "agent"),
      tool: sources.filter((item) => item.source_type === "tool"),
      mcp_server: sources.filter((item) => item.source_type === "mcp_server"),
    }),
    [sources],
  );

  const availableSources = useMemo(
    () => (form.source_type ? sources.filter((item) => item.source_type === form.source_type) : []),
    [sources, form.source_type],
  );

  const selectedSource = useMemo(
    () =>
      sources.find(
        (item) => item.source_type === form.source_type && item.source_id === form.source_id,
      ) ?? null,
    [sources, form.source_type, form.source_id],
  );

  const stats = useMemo(
    () => ({
      total: capabilities.length,
      tool: capabilities.filter((item) => item.kind === "tool").length,
      skill: capabilities.filter((item) => item.kind === "skill").length,
      agent: capabilities.filter((item) => item.kind === "agent").length,
      service: capabilities.filter((item) => item.kind === "service").length,
    }),
    [capabilities],
  );

  function updateField<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleLoadCapability(capability: GraphCapabilityDefinition) {
    setSelectedCapabilityId(capability.id);
    setForm(buildFormFromCapability(capability, form.provider_id));
    setStatusMessage(null);
    setDraftMessage(null);
    setError(null);
  }

  function handleCreateNew() {
    setSelectedCapabilityId("");
    setForm(createEmptyForm(form.provider_id));
    setStatusMessage("已切换到新建模式。");
    setDraftMessage(null);
    setError(null);
  }

  function runDraftFill() {
    setError(null);
    setStatusMessage(null);
    setDraftMessage(null);
    startTransition(async () => {
      try {
        const response = await draftGraphCapability({
          kind: form.kind,
          name: form.name.trim() || "未命名能力",
          description: form.description.trim(),
          provider_id: form.provider_id || null,
          source_type: form.source_type || null,
          source_id: form.source_id || null,
        });
        setForm(buildFormFromCapability(response.capability, form.provider_id));
        setDraftMessage(response.execution_note ?? "已生成能力草稿。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "AI 填写失败。");
      }
    });
  }

  function saveCapability() {
    setError(null);
    setStatusMessage(null);
    setDraftMessage(null);
    startTransition(async () => {
      try {
        const payload = capabilityToPayload(form, selectedSource);
        if (!payload.id || !payload.name || !payload.action) {
          throw new Error("请先填写 ID、名称和动作标识。");
        }
        const isEditingCurrent = Boolean(selectedCapabilityId) && selectedCapabilityId === payload.id;
        const saved = isEditingCurrent
          ? await updateGraphCapability(payload.id, payload)
          : await createGraphCapability(payload);
        setCapabilities((current) => {
          const next = current.filter((item) => item.id !== saved.id);
          return [saved, ...next].sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));
        });
        setSelectedCapabilityId(saved.id);
        setForm(buildFormFromCapability(saved, form.provider_id));
        setStatusMessage(isEditingCurrent ? "原子能力已更新。" : "原子能力已创建。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "保存失败。");
      }
    });
  }

  function removeCapability() {
    if (!selectedCapabilityId) {
      setError("请先选择一个原子能力。");
      return;
    }
    if (!window.confirm(`确认删除原子能力「${selectedCapabilityId}」吗？`)) {
      return;
    }
    setError(null);
    setStatusMessage(null);
    setDraftMessage(null);
    startTransition(async () => {
      try {
        await deleteGraphCapability(selectedCapabilityId);
        setCapabilities((current) => current.filter((item) => item.id !== selectedCapabilityId));
        setSelectedCapabilityId("");
        setForm(createEmptyForm(form.provider_id));
        setStatusMessage("原子能力已删除。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "删除失败。");
      }
    });
  }

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <section className="workspace-brand">
          <div className="workspace-brand__mark">能</div>
          <div>
            <strong>任务驾驶舱</strong>
            <span>原子能力注册</span>
          </div>
        </section>

        <section className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <strong>图谱导航</strong>
          </div>
          <div className="workspace-menu">
            <Link href="/graph" className="workspace-menu__item">
              <div>
                <strong>总览</strong>
                <small>看整体运行健康度</small>
              </div>
            </Link>
            <Link href="/graph/playbooks" className="workspace-menu__item">
              <div>
                <strong>任务剧本</strong>
                <small>查看入口节点和编译结果</small>
              </div>
            </Link>
            <Link href="/graph/capabilities" className="workspace-menu__item workspace-menu__item--active">
              <div>
                <strong>能力注册</strong>
                <small>从 skill / agent / tool / mcp server 注册</small>
              </div>
            </Link>
            <Link href="/graph/composites" className="workspace-menu__item">
              <div>
                <strong>组合链路</strong>
                <small>查看复合执行顺序</small>
              </div>
            </Link>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>能力概况</strong>
              <span>{stats.total} 个已注册原子</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>工具</span>
              <strong>{stats.tool}</strong>
            </article>
            <article className="settings-stat-card">
              <span>技能</span>
              <strong>{stats.skill}</strong>
            </article>
            <article className="settings-stat-card">
              <span>代理</span>
              <strong>{stats.agent}</strong>
            </article>
            <article className="settings-stat-card">
              <span>服务</span>
              <strong>{stats.service}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>来源概况</strong>
              <span>当前应用已暴露的注册源</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>技能</span>
              <strong>{sourceGroups.skill.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>Agent</span>
              <strong>{sourceGroups.agent.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>工具</span>
              <strong>{sourceGroups.tool.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>MCP</span>
              <strong>{sourceGroups.mcp_server.length}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>原子列表</strong>
              <span>点击载入，或新建一个能力</span>
            </div>
            <button type="button" className="settings-cta settings-cta--secondary" onClick={handleCreateNew}>
              新建原子
            </button>
          </div>
          <div className="settings-provider-list">
            {capabilities.length ? (
              capabilities.map((capability) => {
                const isActive = capability.id === selectedCapabilityId;
                return (
                  <article
                    key={capability.id}
                    className={`settings-provider-card ${isActive ? "settings-provider-card--active" : ""}`}
                  >
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>{capability.name}</strong>
                        <span>{capability.id}</span>
                      </div>
                      <em>{KIND_LABELS[capability.kind]}</em>
                    </div>
                    <div className="settings-provider-card__meta">
                      <span>{capability.action}</span>
                      <span>{capability.enabled ? "启用" : "停用"}</span>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => handleLoadCapability(capability)}>
                        载入编辑
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <p className="workspace-empty">还没有原子能力，先点击上方“新建原子”。</p>
            )}
          </div>
        </section>
      </aside>

      <div className="workspace-main">
        <section className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>原子能力注册工作台</strong>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button" onClick={runDraftFill}>
              {isPending ? "处理中..." : "AI 填写参数"}
            </button>
            <button type="button" onClick={saveCapability}>
              {isPending ? "保存中..." : "保存能力"}
            </button>
          </div>
        </section>

        <section className="workspace-panel settings-form-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>{selectedCapability ? "编辑原子能力" : "新建原子能力"}</strong>
              <span>选择 kind 后可调用模型自动补全配置、Schema 与重试策略</span>
            </div>
          </div>

          <form className="settings-form-grid" onSubmit={(event) => event.preventDefault()}>
            <label className="settings-field">
              <span>原子 ID</span>
              <input value={form.id} onChange={(event) => updateField("id", event.target.value)} placeholder="cap_tool_publish_summary" />
            </label>

            <label className="settings-field">
              <span>原子名称</span>
              <input value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="发布摘要" />
            </label>

            <label className="settings-field">
              <span>原子类型</span>
              <select value={form.kind} onChange={(event) => updateField("kind", event.target.value as CapabilityKind)}>
                <option value="tool">tool</option>
                <option value="skill">skill</option>
                <option value="agent">agent</option>
                <option value="service">service</option>
              </select>
            </label>

            <label className="settings-field">
              <span>来源类型</span>
              <select
                value={form.source_type}
                onChange={(event) => {
                  const nextSourceType = event.target.value as CapabilitySourceType | "";
                  updateField("source_type", nextSourceType);
                  updateField("source_id", "");
                  const matchedKind =
                    sources.find((item) => item.source_type === nextSourceType)?.suggested_kind ?? null;
                  if (matchedKind) {
                    updateField("kind", matchedKind);
                  }
                }}
              >
                <option value="">手动定义</option>
                <option value="skill">skill</option>
                <option value="agent">agent</option>
                <option value="tool">tool</option>
                <option value="mcp_server">mcp server</option>
              </select>
            </label>

            <label className="settings-field">
              <span>来源对象</span>
              <select
                value={form.source_id}
                onChange={(event) => {
                  const nextSourceId = event.target.value;
                  updateField("source_id", nextSourceId);
                  const nextSource = availableSources.find((item) => item.source_id === nextSourceId) ?? null;
                  if (nextSource) {
                    updateField("kind", nextSource.suggested_kind);
                    if (!form.name.trim()) {
                      updateField("name", nextSource.name);
                    }
                    if (!form.description.trim()) {
                      updateField("description", nextSource.description);
                    }
                  }
                }}
                disabled={!form.source_type}
              >
                <option value="">{form.source_type ? "请选择来源对象" : "请先选择来源类型"}</option>
                {availableSources.map((source) => (
                  <option key={`${source.source_type}:${source.source_id}`} value={source.source_id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="settings-field">
              <span>动作标识</span>
              <input value={form.action} onChange={(event) => updateField("action", event.target.value)} placeholder="publish.summary" />
            </label>

            <label className="settings-field">
              <span>AI 填写模型</span>
              <select value={form.provider_id} onChange={(event) => updateField("provider_id", event.target.value)}>
                <option value="">不使用模型（走模板）</option>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name} · {provider.model}
                  </option>
                ))}
              </select>
            </label>

            <label className="settings-toggle">
              <input type="checkbox" checked={form.enabled} onChange={(event) => updateField("enabled", event.target.checked)} />
              <div>
                <strong>启用状态</strong>
                <span>关闭后保留定义，但不建议参与新编排</span>
              </div>
            </label>

            <label className="settings-field settings-field--full">
              <span>能力描述</span>
              <textarea value={form.description} onChange={(event) => updateField("description", event.target.value)} placeholder="用中文描述这个原子能力的职责、输入语义和输出目标。" />
            </label>

            <label className="settings-field settings-field--full">
              <span>配置 JSON</span>
              <textarea
                value={form.config}
                onChange={(event) => updateField("config", event.target.value)}
                style={{ minHeight: 180, fontFamily: "Consolas, Monaco, monospace" }}
              />
            </label>

            <label className="settings-field settings-field--full">
              <span>输入 Schema JSON</span>
              <textarea
                value={form.input_schema}
                onChange={(event) => updateField("input_schema", event.target.value)}
                style={{ minHeight: 220, fontFamily: "Consolas, Monaco, monospace" }}
              />
            </label>

            <label className="settings-field settings-field--full">
              <span>输出 Schema JSON</span>
              <textarea
                value={form.output_schema}
                onChange={(event) => updateField("output_schema", event.target.value)}
                style={{ minHeight: 220, fontFamily: "Consolas, Monaco, monospace" }}
              />
            </label>

            <label className="settings-field">
              <span>最大重试次数</span>
              <input
                type="number"
                min={1}
                max={5}
                value={form.retry_max_attempts}
                onChange={(event) => updateField("retry_max_attempts", Number(event.target.value) || 1)}
              />
            </label>

            <label className="settings-field">
              <span>退避秒数</span>
              <input
                type="number"
                min={0}
                max={300}
                step={0.5}
                value={form.retry_backoff_seconds}
                onChange={(event) => updateField("retry_backoff_seconds", Number(event.target.value) || 0)}
              />
            </label>

            <label className="settings-field settings-field--full">
              <span>重试触发条件</span>
              <input value={form.retry_on} onChange={(event) => updateField("retry_on", event.target.value)} placeholder="timeout, rate_limit, 5xx" />
            </label>

            <div className="settings-form-actions settings-field--full">
              <button
                type="button"
                className="settings-cta settings-cta--primary"
                disabled={isPending}
                onClick={saveCapability}
              >
                {isPending ? "处理中..." : selectedCapability ? "更新原子能力" : "创建原子能力"}
              </button>

              <button
                type="button"
                className="settings-cta settings-cta--secondary"
                disabled={isPending || !form.kind}
                onClick={runDraftFill}
              >
                {isPending ? "处理中..." : "AI 填写参数"}
              </button>

              <button
                type="button"
                className="settings-cta settings-cta--secondary"
                disabled={isPending || !selectedCapability}
                onClick={removeCapability}
              >
                删除当前原子
              </button>
            </div>
          </form>
        </section>

        {statusMessage ? <p className="workspace-status workspace-status--success">{statusMessage}</p> : null}
        {draftMessage ? <p className="workspace-status">{draftMessage}</p> : null}
        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </div>

      <aside className="workspace-rightbar">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>当前焦点</strong>
              <span>{selectedCapability?.name ?? "新建原子能力"}</span>
            </div>
          </div>
          <div className="workspace-summary">
            <h3>一、当前类型</h3>
            <p>{KIND_LABELS[form.kind]}：{form.description || "先选择类型，再补中文职责描述。"}</p>
            <h3>二、编排建议</h3>
            <ul>
              <li>tool 适合本地函数或明确的单步工具调用</li>
              <li>skill 适合复用已有 Skill 资产</li>
              <li>agent 适合需要推理和多轮约束的原子任务</li>
              <li>service 适合封装外部接口或内部服务能力</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>调用摘要</strong>
              <span>保存前再核对一次关键字段</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{form.action || "等待填写动作标识"}</h3>
            <p>{form.id || "建议用 cap_kind_name 形式稳定命名。"}</p>
            <div className="settings-focus__tags">
              <span>{form.enabled ? "已启用" : "已停用"}</span>
              <span>{providers.find((provider) => provider.id === form.provider_id)?.name ?? "模板生成"}</span>
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>落地提示</strong>
              <span>给原子注册页的使用约束</span>
            </div>
          </div>
          <div className="workspace-summary">
            <ul>
              <li>可直接从现有 skill、agent、tool 和 mcp server 注册原子能力</li>
              <li>删除前会校验是否仍被 composite 或 playbook 引用</li>
              <li>AI 填写失败时会自动回退到模板草稿</li>
              <li>Schema 与 config 都必须保存为 JSON 对象</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>来源详情</strong>
              <span>{selectedSource?.name ?? "未选择来源对象"}</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{selectedSource?.name ?? "等待选择来源"}</h3>
            <p>{selectedSource?.description ?? "选择现有 skill、agent、tool 或 mcp server 后，AI 会基于该来源生成参数草稿。"}</p>
            <div className="settings-focus__tags">
              <span>{selectedSource?.source_type ?? "source-type"}</span>
              <span>{selectedSource?.source_id ?? "source-id"}</span>
            </div>
          </div>
        </section>
      </aside>
    </section>
  );
}
