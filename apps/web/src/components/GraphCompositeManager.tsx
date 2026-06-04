"use client";

import { useMemo, useState, useTransition } from "react";

import type { GraphCapabilityDefinition, GraphCompileResult, GraphCompositeDefinition, GraphCompositeNodeDefinition } from "@/lib/api";
import {
  compileGraphComposite,
  createGraphComposite,
  deleteGraphComposite,
  updateGraphComposite,
} from "@/lib/api";

type GraphCompositeManagerProps = {
  initialComposites: GraphCompositeDefinition[];
  capabilities: GraphCapabilityDefinition[];
  compileResults: Record<string, GraphCompileResult>;
};

type CompositeNodeForm = {
  id: string;
  capability_id: string;
  order: number;
  input_mapping: string;
};

type FormState = {
  id: string;
  name: string;
  mode: "chain";
  description: string;
  created_at: string;
  nodes: CompositeNodeForm[];
};

function prettyJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

function buildNodeForm(node: GraphCompositeNodeDefinition): CompositeNodeForm {
  return {
    id: node.id,
    capability_id: node.capability_id,
    order: node.order,
    input_mapping: prettyJson(node.input_mapping),
  };
}

function buildFormFromComposite(composite: GraphCompositeDefinition): FormState {
  return {
    id: composite.id,
    name: composite.name,
    mode: composite.mode,
    description: composite.description,
    created_at: composite.created_at,
    nodes: composite.nodes
      .slice()
      .sort((left, right) => left.order - right.order)
      .map(buildNodeForm),
  };
}

function createEmptyNode(index: number, capabilityId = ""): CompositeNodeForm {
  return {
    id: `step_${index + 1}`,
    capability_id: capabilityId,
    order: index + 1,
    input_mapping: "{}",
  };
}

function createEmptyForm(defaultCapabilityId = ""): FormState {
  return {
    id: "",
    name: "",
    mode: "chain",
    description: "",
    created_at: new Date().toISOString(),
    nodes: [createEmptyNode(0, defaultCapabilityId)],
  };
}

function parseJsonField(value: string) {
  try {
    const parsed = JSON.parse(value || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("input mapping 必须是 JSON 对象");
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message.includes("必须是 JSON 对象")) {
      throw error;
    }
    throw new Error("input mapping 不是合法 JSON");
  }
}

function compositeToPayload(form: FormState): GraphCompositeDefinition {
  return {
    id: form.id.trim(),
    name: form.name.trim(),
    mode: "chain",
    description: form.description.trim(),
    created_at: form.created_at,
    nodes: form.nodes.map((node, index) => ({
      id: node.id.trim(),
      capability_id: node.capability_id,
      order: index + 1,
      input_mapping: parseJsonField(node.input_mapping),
    })),
  };
}

export function GraphCompositeManager({
  initialComposites,
  capabilities,
  compileResults,
}: GraphCompositeManagerProps) {
  const [composites, setComposites] = useState(initialComposites);
  const [selectedCompositeId, setSelectedCompositeId] = useState(initialComposites[0]?.id ?? "");
  const [form, setForm] = useState<FormState>(() =>
    initialComposites[0] ? buildFormFromComposite(initialComposites[0]) : createEmptyForm(initialComposites[0]?.nodes[0]?.capability_id ?? capabilities[0]?.id ?? "")
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localCompileResults, setLocalCompileResults] = useState<Record<string, GraphCompileResult>>(compileResults);
  const [isPending, startTransition] = useTransition();

  const selectedComposite = useMemo(
    () => composites.find((item) => item.id === selectedCompositeId) ?? null,
    [composites, selectedCompositeId]
  );

  function updateField<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateNode(index: number, patch: Partial<CompositeNodeForm>) {
    setForm((current) => ({
      ...current,
      nodes: current.nodes.map((node, nodeIndex) =>
        nodeIndex === index ? { ...node, ...patch, order: nodeIndex + 1 } : node
      ),
    }));
  }

  function handleCreateNew() {
    setSelectedCompositeId("");
    setForm(createEmptyForm(capabilities[0]?.id ?? ""));
    setStatusMessage(null);
    setError(null);
  }

  function handleLoadComposite(composite: GraphCompositeDefinition) {
    setSelectedCompositeId(composite.id);
    setForm(buildFormFromComposite(composite));
    setStatusMessage(null);
    setError(null);
  }

  function addNode() {
    setForm((current) => ({
      ...current,
      nodes: [...current.nodes, createEmptyNode(current.nodes.length, capabilities[0]?.id ?? "")],
    }));
  }

  function removeNode(index: number) {
    setForm((current) => {
      const nextNodes = current.nodes.filter((_, nodeIndex) => nodeIndex !== index);
      return {
        ...current,
        nodes: (nextNodes.length ? nextNodes : [createEmptyNode(0, capabilities[0]?.id ?? "")]).map((node, nodeIndex) => ({
          ...node,
          order: nodeIndex + 1,
        })),
      };
    });
  }

  function moveNode(index: number, direction: -1 | 1) {
    setForm((current) => {
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= current.nodes.length) {
        return current;
      }
      const nextNodes = current.nodes.slice();
      const [currentNode] = nextNodes.splice(index, 1);
      nextNodes.splice(targetIndex, 0, currentNode);
      return {
        ...current,
        nodes: nextNodes.map((node, nodeIndex) => ({ ...node, order: nodeIndex + 1 })),
      };
    });
  }

  function saveComposite() {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const payload = compositeToPayload(form);
        const exists = composites.some((item) => item.id === payload.id);
        const saved = exists
          ? await updateGraphComposite(payload.id, payload)
          : await createGraphComposite(payload);
        const compile = await compileGraphComposite(saved.id);
        setComposites((current) => {
          const next = current.filter((item) => item.id !== saved.id);
          return [saved, ...next];
        });
        setLocalCompileResults((current) => ({ ...current, [saved.id]: compile }));
        setSelectedCompositeId(saved.id);
        setForm(buildFormFromComposite(saved));
        setStatusMessage(exists ? "分子层 composite 已更新。" : "分子层 composite 已创建。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "保存 composite 失败。");
      }
    });
  }

  function removeComposite() {
    if (!selectedCompositeId) {
      setError("请先选择一个 composite。");
      return;
    }
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        await deleteGraphComposite(selectedCompositeId);
        const next = composites.filter((item) => item.id !== selectedCompositeId);
        setComposites(next);
        setLocalCompileResults((current) => {
          const updated = { ...current };
          delete updated[selectedCompositeId];
          return updated;
        });
        setSelectedCompositeId("");
        setForm(createEmptyForm(capabilities[0]?.id ?? ""));
        setStatusMessage("分子层 composite 已删除。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "删除 composite 失败。");
      }
    });
  }

  function runCompile() {
    if (!form.id.trim()) {
      setError("请先填写 composite ID 后再编译。");
      return;
    }
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const payload = compositeToPayload(form);
        const compile = await compileGraphComposite(payload.id);
        setLocalCompileResults((current) => ({ ...current, [payload.id]: compile }));
        setStatusMessage(compile.ok ? "编译通过。" : "编译完成，请查看错误和告警。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "编译 composite 失败。");
      }
    });
  }

  const selectedCompile = selectedCompositeId ? localCompileResults[selectedCompositeId] : null;

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <section className="workspace-brand">
          <div className="workspace-brand__mark">链</div>
          <div>
            <strong>任务驾驶舱</strong>
            <span>分子层 Composite 配置</span>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>Composite 概况</strong>
              <span>{composites.length} 条链路</span>
            </div>
            <button type="button" className="settings-cta settings-cta--secondary" onClick={handleCreateNew}>
              新建分子
            </button>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>总数</span>
              <strong>{composites.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>能力池</span>
              <strong>{capabilities.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>编译异常</span>
              <strong>{Object.values(localCompileResults).filter((item) => !item.ok).length}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>分子链路列表</strong>
              <span>选择后在中间编辑配置</span>
            </div>
          </div>
          <div className="settings-provider-list">
            {composites.length ? (
              composites.map((composite) => {
                const compile = localCompileResults[composite.id];
                const isActive = composite.id === selectedCompositeId;
                return (
                  <article
                    key={composite.id}
                    className={`settings-provider-card ${isActive ? "settings-provider-card--active" : ""}`}
                  >
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>{composite.name}</strong>
                        <span>{composite.id}</span>
                      </div>
                      <em>{compile?.ok ? "可运行" : "待修复"}</em>
                    </div>
                    <div className="settings-provider-card__meta">
                      <span>{composite.mode}</span>
                      <span>{composite.nodes.length} 节点</span>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => handleLoadComposite(composite)}>
                        载入编辑
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <p className="workspace-empty">还没有 composite，先创建一个分子层链路。</p>
            )}
          </div>
        </section>
      </aside>

      <div className="workspace-main">
        <section className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>分子层 Composite 工作台</strong>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button" onClick={runCompile}>
              {isPending ? "处理中..." : "编译检查"}
            </button>
            <button type="button" onClick={saveComposite}>
              {isPending ? "保存中..." : "保存分子"}
            </button>
          </div>
        </section>

        <section className="workspace-panel settings-form-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>{selectedComposite ? "编辑分子层 composite" : "新建分子层 composite"}</strong>
              <span>用 chain 方式把多个原子能力串成稳定的中间层任务。</span>
            </div>
          </div>

          <form className="settings-form-grid" onSubmit={(event) => event.preventDefault()}>
            <label className="settings-field">
              <span>Composite ID</span>
              <input value={form.id} onChange={(event) => updateField("id", event.target.value)} placeholder="comp_publish_summary" />
            </label>

            <label className="settings-field">
              <span>Composite 名称</span>
              <input value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="发布摘要链路" />
            </label>

            <label className="settings-field">
              <span>模式</span>
              <select value={form.mode} onChange={() => updateField("mode", "chain")}>
                <option value="chain">chain</option>
              </select>
            </label>

            <label className="settings-field settings-field--full">
              <span>描述</span>
              <textarea
                value={form.description}
                onChange={(event) => updateField("description", event.target.value)}
                placeholder="描述这个分子层 composite 在业务链路中的职责边界。"
                style={{ minHeight: 160 }}
              />
            </label>

            <div className="settings-field settings-field--full">
              <div className="workspace-panel__header">
                <div>
                  <strong>链路节点</strong>
                  <span>按顺序编排 capability，可上下调整顺序。</span>
                </div>
                <button type="button" className="settings-cta settings-cta--secondary" onClick={addNode}>
                  添加节点
                </button>
              </div>
              <div className="settings-provider-list">
                {form.nodes.map((node, index) => (
                  <article key={`${node.id}-${index}`} className="settings-provider-card">
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>节点 {index + 1}</strong>
                        <span>order {index + 1}</span>
                      </div>
                      <em>{capabilities.find((capability) => capability.id === node.capability_id)?.kind ?? "未选能力"}</em>
                    </div>
                    <div className="settings-form-grid">
                      <label className="settings-field">
                        <span>节点 ID</span>
                        <input
                          value={node.id}
                          onChange={(event) => updateNode(index, { id: event.target.value })}
                          placeholder={`step_${index + 1}`}
                        />
                      </label>
                      <label className="settings-field">
                        <span>原子能力</span>
                        <select
                          value={node.capability_id}
                          onChange={(event) => updateNode(index, { capability_id: event.target.value })}
                        >
                          <option value="">请选择 capability</option>
                          {capabilities.map((capability) => (
                            <option key={capability.id} value={capability.id}>
                              {capability.name} · {capability.id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="settings-field settings-field--full">
                        <span>输入映射 JSON</span>
                        <textarea
                          value={node.input_mapping}
                          onChange={(event) => updateNode(index, { input_mapping: event.target.value })}
                          style={{ minHeight: 140, fontFamily: "Consolas, Monaco, monospace" }}
                        />
                      </label>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => moveNode(index, -1)} disabled={index === 0}>
                        上移
                      </button>
                      <button type="button" onClick={() => moveNode(index, 1)} disabled={index === form.nodes.length - 1}>
                        下移
                      </button>
                      <button type="button" onClick={() => removeNode(index)} disabled={form.nodes.length === 1}>
                        删除节点
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="settings-form-actions settings-field--full">
              <button type="button" className="settings-cta settings-cta--primary" onClick={saveComposite} disabled={isPending}>
                {isPending ? "处理中..." : selectedComposite ? "更新分子层 composite" : "创建分子层 composite"}
              </button>
              <button type="button" className="settings-cta settings-cta--secondary" onClick={runCompile} disabled={isPending}>
                {isPending ? "处理中..." : "编译检查"}
              </button>
              <button type="button" className="settings-cta settings-cta--secondary" onClick={removeComposite} disabled={isPending || !selectedComposite}>
                删除当前分子
              </button>
            </div>
          </form>
        </section>

        {statusMessage ? <p className="workspace-status workspace-status--success">{statusMessage}</p> : null}
        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </div>

      <aside className="workspace-rightbar">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>当前分子摘要</strong>
              <span>{selectedComposite?.name ?? "新建分子层 composite"}</span>
            </div>
          </div>
          <div className="workspace-summary">
            <h3>一、结构建议</h3>
            <p>一个分子层 composite 最好只做一段有界任务，保持 2 到 10 个 capability 的清晰串联。</p>
            <h3>二、编排提示</h3>
            <ul>
              <li>节点顺序必须从 1 开始连续递增</li>
              <li>优先把 capability 的输出语义在映射里显式写清楚</li>
              <li>如果 warning 太多，说明链路职责可能需要继续拆分</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>编译结果</strong>
              <span>保存后可立即检查结构合法性</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{selectedCompile ? (selectedCompile.ok ? "编译通过" : "存在问题") : "等待编译"}</h3>
            <p>{selectedCompile ? `errors: ${selectedCompile.errors.length} · warnings: ${selectedCompile.warnings.length}` : "点击编译检查查看结果。"}</p>
            <div className="settings-focus__tags">
              {(selectedCompile?.errors ?? []).slice(0, 3).map((item) => (
                <span key={`error-${item}`}>{item}</span>
              ))}
              {(selectedCompile?.warnings ?? []).slice(0, 3).map((item) => (
                <span key={`warning-${item}`}>{item}</span>
              ))}
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>可用原子能力</strong>
              <span>当前可接入的 capability 池</span>
            </div>
          </div>
          <div className="settings-capability-list">
            {capabilities.slice(0, 10).map((capability) => (
              <span key={capability.id}>{capability.name}</span>
            ))}
          </div>
        </section>
      </aside>
    </section>
  );
}
