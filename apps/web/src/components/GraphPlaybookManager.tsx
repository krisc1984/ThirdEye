"use client";

import { useMemo, useState, useTransition } from "react";

import type {
  GraphCapabilityDefinition,
  GraphCompileResult,
  GraphCompositeDefinition,
  GraphEdgeDefinition,
  GraphNodeDefinition,
  GraphPlaybookDefinition,
} from "@/lib/api";
import {
  compileGraphPlaybook,
  createGraphPlaybook,
  deleteGraphPlaybook,
  updateGraphPlaybook,
} from "@/lib/api";

type GraphPlaybookManagerProps = {
  initialPlaybooks: GraphPlaybookDefinition[];
  capabilities: GraphCapabilityDefinition[];
  composites: GraphCompositeDefinition[];
  compileResults: Record<string, GraphCompileResult>;
};

type PlaybookNodeForm = {
  id: string;
  type: GraphNodeDefinition["type"];
  capability_id: string;
  composite_id: string;
  approval_label: string;
  config: string;
};

type PlaybookEdgeForm = {
  source: string;
  target: string;
  condition: string;
};

type FormState = {
  id: string;
  name: string;
  version: string;
  description: string;
  entry_node_id: string;
  created_at: string;
  nodes: PlaybookNodeForm[];
  edges: PlaybookEdgeForm[];
};

function prettyJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

function buildNodeForm(node: GraphNodeDefinition): PlaybookNodeForm {
  return {
    id: node.id,
    type: node.type,
    capability_id: node.capability_id ?? "",
    composite_id: node.composite_id ?? "",
    approval_label: node.approval_label ?? "",
    config: prettyJson(node.config),
  };
}

function buildEdgeForm(edge: GraphEdgeDefinition): PlaybookEdgeForm {
  return {
    source: edge.source,
    target: edge.target,
    condition: edge.condition ?? "",
  };
}

function buildFormFromPlaybook(playbook: GraphPlaybookDefinition): FormState {
  return {
    id: playbook.id,
    name: playbook.name,
    version: playbook.version,
    description: playbook.description,
    entry_node_id: playbook.entry_node_id,
    created_at: playbook.created_at,
    nodes: playbook.nodes.map(buildNodeForm),
    edges: playbook.edges.map(buildEdgeForm),
  };
}

function createEmptyNode(index: number): PlaybookNodeForm {
  return {
    id: `node_${index + 1}`,
    type: "composite",
    capability_id: "",
    composite_id: "",
    approval_label: "",
    config: "{}",
  };
}

function createEmptyEdge(): PlaybookEdgeForm {
  return {
    source: "",
    target: "",
    condition: "",
  };
}

function createEmptyForm(): FormState {
  return {
    id: "",
    name: "",
    version: "1.0.0",
    description: "",
    entry_node_id: "",
    created_at: new Date().toISOString(),
    nodes: [createEmptyNode(0)],
    edges: [],
  };
}

type TopologyNodePreview = {
  id: string;
  type: GraphNodeDefinition["type"];
  title: string;
  subtitle: string;
  outgoing: GraphEdgeDefinition[];
  incomingCount: number;
  isEntry: boolean;
};

type TopologyCanvasNode = TopologyNodePreview & {
  x: number;
  y: number;
  width: number;
  height: number;
  column: number;
  row: number;
};

type TopologyCanvasEdge = {
  key: string;
  source: TopologyCanvasNode;
  target: TopologyCanvasNode;
  condition: string;
};

function nodeTypeLabel(type: GraphNodeDefinition["type"]) {
  if (type === "human_approval") {
    return "approval";
  }
  return type;
}

function nodeAccent(type: GraphNodeDefinition["type"], isEntry: boolean) {
  if (isEntry) {
    return {
      fill: "rgba(79, 124, 255, 0.16)",
      stroke: "rgba(79, 124, 255, 0.72)",
      badge: "#4f7cff",
    };
  }
  if (type === "human_approval") {
    return {
      fill: "rgba(255, 155, 82, 0.16)",
      stroke: "rgba(255, 155, 82, 0.65)",
      badge: "#ff9b52",
    };
  }
  if (type === "capability") {
    return {
      fill: "rgba(66, 181, 154, 0.16)",
      stroke: "rgba(66, 181, 154, 0.65)",
      badge: "#42b59a",
    };
  }
  return {
    fill: "rgba(124, 134, 155, 0.12)",
    stroke: "rgba(124, 134, 155, 0.44)",
    badge: "#7c869b",
  };
}

function parseJsonField(value: string) {
  try {
    const parsed = JSON.parse(value || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("节点 config 必须是 JSON 对象");
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    if (error instanceof Error && error.message.includes("必须是 JSON 对象")) {
      throw error;
    }
    throw new Error("节点 config 不是合法 JSON");
  }
}

function playbookToPayload(form: FormState): GraphPlaybookDefinition {
  return {
    id: form.id.trim(),
    name: form.name.trim(),
    version: form.version.trim(),
    description: form.description.trim(),
    entry_node_id: form.entry_node_id.trim(),
    created_at: form.created_at,
    nodes: form.nodes.map((node) => ({
      id: node.id.trim(),
      type: node.type,
      capability_id: node.type === "capability" ? node.capability_id : null,
      composite_id: node.type === "composite" ? node.composite_id : null,
      approval_label: node.type === "human_approval" ? node.approval_label.trim() || node.id.trim() : null,
      config: parseJsonField(node.config),
    })),
    edges: form.edges.map((edge) => ({
      source: edge.source.trim(),
      target: edge.target.trim(),
      condition: edge.condition.trim() || null,
    })),
  };
}

export function GraphPlaybookManager({
  initialPlaybooks,
  capabilities,
  composites,
  compileResults,
}: GraphPlaybookManagerProps) {
  const [playbooks, setPlaybooks] = useState(initialPlaybooks);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState(initialPlaybooks[0]?.id ?? "");
  const [form, setForm] = useState<FormState>(() =>
    initialPlaybooks[0] ? buildFormFromPlaybook(initialPlaybooks[0]) : createEmptyForm()
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [localCompileResults, setLocalCompileResults] = useState<Record<string, GraphCompileResult>>(compileResults);
  const [isPending, startTransition] = useTransition();

  const selectedPlaybook = useMemo(
    () => playbooks.find((item) => item.id === selectedPlaybookId) ?? null,
    [playbooks, selectedPlaybookId]
  );

  const availableNodeIds = useMemo(
    () => form.nodes.map((node) => node.id).filter(Boolean),
    [form.nodes]
  );

  const topologyPreview = useMemo<TopologyNodePreview[]>(() => {
    const outgoingMap = new Map<string, GraphEdgeDefinition[]>();
    const incomingCountMap = new Map<string, number>();

    for (const edge of form.edges) {
      const source = edge.source.trim();
      const target = edge.target.trim();
      if (!source || !target) {
        continue;
      }
      outgoingMap.set(source, [...(outgoingMap.get(source) ?? []), edge]);
      incomingCountMap.set(target, (incomingCountMap.get(target) ?? 0) + 1);
    }

    return form.nodes.map((node) => {
      const subtitle =
        node.type === "composite"
          ? node.composite_id || "未绑定 composite"
          : node.type === "capability"
            ? node.capability_id || "未绑定 capability"
            : node.approval_label || "未设置审批标签";
      return {
        id: node.id.trim(),
        type: node.type,
        title: node.id.trim() || "未命名节点",
        subtitle,
        outgoing: outgoingMap.get(node.id.trim()) ?? [],
        incomingCount: incomingCountMap.get(node.id.trim()) ?? 0,
        isEntry: form.entry_node_id.trim() === node.id.trim(),
      };
    });
  }, [form.edges, form.entry_node_id, form.nodes]);

  const validationHints = useMemo(() => {
    const hints: string[] = [];
    if (!form.entry_node_id.trim()) {
      hints.push("还没有设置入口节点。");
    }
    const nodeIds = new Set(form.nodes.map((node) => node.id.trim()).filter(Boolean));
    const orphanNodes = topologyPreview.filter((node) => !node.isEntry && node.incomingCount === 0);
    if (orphanNodes.length) {
      hints.push(`存在未接入主链的节点：${orphanNodes.map((node) => node.title).join("、")}`);
    }
    const brokenEdges = form.edges.filter(
      (edge) => edge.source.trim() && edge.target.trim() && (!nodeIds.has(edge.source.trim()) || !nodeIds.has(edge.target.trim()))
    );
    if (brokenEdges.length) {
      hints.push(`有 ${brokenEdges.length} 条边引用了不存在的节点。`);
    }
    for (const node of form.nodes) {
      if (node.type !== "human_approval") {
        continue;
      }
      const conditions = new Set(
        form.edges
          .filter((edge) => edge.source.trim() === node.id.trim())
          .map((edge) => edge.condition.trim())
          .filter(Boolean)
      );
      if (!conditions.has("approve") || !conditions.has("reject")) {
        hints.push(`审批节点 ${node.id || "未命名"} 缺少 approve / reject 出口。`);
      }
    }
    return hints;
  }, [form.edges, form.entry_node_id, form.nodes, topologyPreview]);

  const topologyCanvas = useMemo(() => {
    const nodeById = new Map(topologyPreview.map((node) => [node.id, node] as const));
    const validNodes = topologyPreview.filter((node) => node.id);

    if (!validNodes.length) {
      return {
        nodes: [] as TopologyCanvasNode[],
        edges: [] as TopologyCanvasEdge[],
        width: 720,
        height: 240,
      };
    }

    const adjacency = new Map<string, string[]>();
    const indegree = new Map<string, number>();
    for (const node of validNodes) {
      adjacency.set(node.id, []);
      indegree.set(node.id, 0);
    }

    for (const edge of form.edges) {
      const source = edge.source.trim();
      const target = edge.target.trim();
      if (!adjacency.has(source) || !nodeById.has(target)) {
        continue;
      }
      adjacency.get(source)?.push(target);
      indegree.set(target, (indegree.get(target) ?? 0) + 1);
    }

    const entryId = form.entry_node_id.trim();
    const queue: string[] = [];
    const levelMap = new Map<string, number>();

    if (entryId && nodeById.has(entryId)) {
      queue.push(entryId);
      levelMap.set(entryId, 0);
    }

    for (const node of validNodes) {
      if ((indegree.get(node.id) ?? 0) === 0 && !levelMap.has(node.id)) {
        queue.push(node.id);
        levelMap.set(node.id, entryId && node.id !== entryId ? 1 : 0);
      }
    }

    while (queue.length) {
      const current = queue.shift();
      if (!current) {
        continue;
      }
      const currentLevel = levelMap.get(current) ?? 0;
      for (const next of adjacency.get(current) ?? []) {
        const nextLevel = currentLevel + 1;
        if (!levelMap.has(next) || nextLevel > (levelMap.get(next) ?? 0)) {
          levelMap.set(next, nextLevel);
          queue.push(next);
        }
      }
    }

    for (const node of validNodes) {
      if (!levelMap.has(node.id)) {
        levelMap.set(node.id, 0);
      }
    }

    const columns = new Map<number, TopologyNodePreview[]>();
    for (const node of validNodes) {
      const column = levelMap.get(node.id) ?? 0;
      columns.set(column, [...(columns.get(column) ?? []), node]);
    }

    const sortedColumns = [...columns.entries()]
      .sort((left, right) => left[0] - right[0])
      .map(([column, nodes]) => [
        column,
        [...nodes].sort((left, right) => {
          if (left.isEntry !== right.isEntry) {
            return left.isEntry ? -1 : 1;
          }
          if (left.type !== right.type) {
            return left.type.localeCompare(right.type);
          }
          return left.title.localeCompare(right.title);
        }),
      ] as const);

    const cardWidth = 176;
    const cardHeight = 88;
    const gapX = 72;
    const gapY = 34;
    const paddingX = 28;
    const paddingY = 28;

    const positionedNodes: TopologyCanvasNode[] = [];
    let maxRows = 1;
    for (const [, nodes] of sortedColumns) {
      maxRows = Math.max(maxRows, nodes.length);
    }

    for (const [column, nodes] of sortedColumns) {
      nodes.forEach((node, row) => {
        positionedNodes.push({
          ...node,
          column,
          row,
          width: cardWidth,
          height: cardHeight,
          x: paddingX + column * (cardWidth + gapX),
          y: paddingY + row * (cardHeight + gapY),
        });
      });
    }

    const nodePositionMap = new Map(positionedNodes.map((node) => [node.id, node] as const));
    const canvasEdges: TopologyCanvasEdge[] = form.edges
      .map((edge, index) => {
        const source = nodePositionMap.get(edge.source.trim());
        const target = nodePositionMap.get(edge.target.trim());
        if (!source || !target) {
          return null;
        }
        return {
          key: `${source.id}-${target.id}-${edge.condition ?? "default"}-${index}`,
          source,
          target,
          condition: edge.condition.trim(),
        };
      })
      .filter((edge): edge is TopologyCanvasEdge => Boolean(edge));

    const width =
      paddingX * 2 +
      Math.max(1, sortedColumns.length) * cardWidth +
      Math.max(0, sortedColumns.length - 1) * gapX;
    const height = paddingY * 2 + maxRows * cardHeight + Math.max(0, maxRows - 1) * gapY;

    return {
      nodes: positionedNodes,
      edges: canvasEdges,
      width,
      height,
    };
  }, [form.edges, form.entry_node_id, topologyPreview]);

  function updateField<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateNode(index: number, patch: Partial<PlaybookNodeForm>) {
    setForm((current) => ({
      ...current,
      nodes: current.nodes.map((node, nodeIndex) => (nodeIndex === index ? { ...node, ...patch } : node)),
    }));
  }

  function updateEdge(index: number, patch: Partial<PlaybookEdgeForm>) {
    setForm((current) => ({
      ...current,
      edges: current.edges.map((edge, edgeIndex) => (edgeIndex === index ? { ...edge, ...patch } : edge)),
    }));
  }

  function handleCreateNew() {
    setSelectedPlaybookId("");
    setForm(createEmptyForm());
    setStatusMessage(null);
    setError(null);
  }

  function handleLoadPlaybook(playbook: GraphPlaybookDefinition) {
    setSelectedPlaybookId(playbook.id);
    setForm(buildFormFromPlaybook(playbook));
    setStatusMessage(null);
    setError(null);
  }

  function addNode() {
    setForm((current) => ({
      ...current,
      nodes: [...current.nodes, createEmptyNode(current.nodes.length)],
    }));
  }

  function removeNode(index: number) {
    setForm((current) => ({
      ...current,
      nodes: current.nodes.filter((_, nodeIndex) => nodeIndex !== index),
      edges: current.edges.filter(
        (edge) => edge.source !== current.nodes[index]?.id && edge.target !== current.nodes[index]?.id
      ),
    }));
  }

  function addEdge() {
    setForm((current) => ({
      ...current,
      edges: [...current.edges, createEmptyEdge()],
    }));
  }

  function removeEdge(index: number) {
    setForm((current) => ({
      ...current,
      edges: current.edges.filter((_, edgeIndex) => edgeIndex !== index),
    }));
  }

  function savePlaybook() {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const payload = playbookToPayload(form);
        const exists = playbooks.some((item) => item.id === payload.id);
        const saved = exists
          ? await updateGraphPlaybook(payload.id, payload)
          : await createGraphPlaybook(payload);
        const compile = await compileGraphPlaybook(saved.id);
        setPlaybooks((current) => {
          const next = current.filter((item) => item.id !== saved.id);
          return [saved, ...next];
        });
        setLocalCompileResults((current) => ({ ...current, [saved.id]: compile }));
        setSelectedPlaybookId(saved.id);
        setForm(buildFormFromPlaybook(saved));
        setStatusMessage(exists ? "复合层剧本已更新。" : "复合层剧本已创建。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "保存剧本失败。");
      }
    });
  }

  function removePlaybook() {
    if (!selectedPlaybookId) {
      setError("请先选择一个剧本。");
      return;
    }
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        await deleteGraphPlaybook(selectedPlaybookId);
        const next = playbooks.filter((item) => item.id !== selectedPlaybookId);
        setPlaybooks(next);
        setLocalCompileResults((current) => {
          const updated = { ...current };
          delete updated[selectedPlaybookId];
          return updated;
        });
        setSelectedPlaybookId("");
        setForm(createEmptyForm());
        setStatusMessage("复合层剧本已删除。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "删除剧本失败。");
      }
    });
  }

  function runCompile() {
    if (!form.id.trim()) {
      setError("请先填写剧本 ID 后再编译。");
      return;
    }
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const payload = playbookToPayload(form);
        const compile = await compileGraphPlaybook(payload.id);
        setLocalCompileResults((current) => ({ ...current, [payload.id]: compile }));
        setStatusMessage(compile.ok ? "剧本编译通过。" : "剧本编译完成，请检查错误和告警。");
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "编译剧本失败。");
      }
    });
  }

  const selectedCompile = selectedPlaybookId ? localCompileResults[selectedPlaybookId] : null;

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <section className="workspace-brand">
          <div className="workspace-brand__mark">剧</div>
          <div>
            <strong>任务驾驶舱</strong>
            <span>复合层剧本配置</span>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>剧本概况</strong>
              <span>{playbooks.length} 份剧本</span>
            </div>
            <button type="button" className="settings-cta settings-cta--secondary" onClick={handleCreateNew}>
              新建剧本
            </button>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>剧本数</span>
              <strong>{playbooks.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>分子链路</span>
              <strong>{composites.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>原子能力</span>
              <strong>{capabilities.length}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>剧本列表</strong>
              <span>载入已有定义或切换到新建状态</span>
            </div>
          </div>
          <div className="settings-provider-list">
            {playbooks.length ? (
              playbooks.map((playbook) => {
                const compile = localCompileResults[playbook.id];
                const isActive = playbook.id === selectedPlaybookId;
                return (
                  <article
                    key={playbook.id}
                    className={`settings-provider-card ${isActive ? "settings-provider-card--active" : ""}`}
                  >
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>{playbook.name}</strong>
                        <span>{playbook.id}</span>
                      </div>
                      <em>{compile?.ok ? "可运行" : "待修复"}</em>
                    </div>
                    <div className="settings-provider-card__meta">
                      <span>{playbook.version}</span>
                      <span>{playbook.entry_node_id || "未设入口"}</span>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => handleLoadPlaybook(playbook)}>
                        载入编辑
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <p className="workspace-empty">还没有复合层剧本，先创建一个顶层流程。</p>
            )}
          </div>
        </section>
      </aside>

      <div className="workspace-main">
        <section className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>复合层剧本工作台</strong>
          </div>
          <div className="workspace-topbar__actions">
            <button type="button" onClick={runCompile}>
              {isPending ? "处理中..." : "编译检查"}
            </button>
            <button type="button" onClick={savePlaybook}>
              {isPending ? "保存中..." : "保存剧本"}
            </button>
          </div>
        </section>

        <section className="workspace-panel settings-form-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>{selectedPlaybook ? "编辑复合层剧本" : "新建复合层剧本"}</strong>
              <span>定义入口节点、拓扑关系、审批出口和复合层编排结构。</span>
            </div>
          </div>

          <form className="settings-form-grid" onSubmit={(event) => event.preventDefault()}>
            <label className="settings-field">
              <span>剧本 ID</span>
              <input value={form.id} onChange={(event) => updateField("id", event.target.value)} placeholder="graph_publish_flow" />
            </label>

            <label className="settings-field">
              <span>剧本名称</span>
              <input value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="发布审批流" />
            </label>

            <label className="settings-field">
              <span>版本</span>
              <input value={form.version} onChange={(event) => updateField("version", event.target.value)} placeholder="1.0.0" />
            </label>

            <label className="settings-field">
              <span>入口节点</span>
              <select value={form.entry_node_id} onChange={(event) => updateField("entry_node_id", event.target.value)}>
                <option value="">请选择入口节点</option>
                {availableNodeIds.map((nodeId) => (
                  <option key={nodeId} value={nodeId}>
                    {nodeId}
                  </option>
                ))}
              </select>
            </label>

            <label className="settings-field settings-field--full">
              <span>描述</span>
              <textarea
                value={form.description}
                onChange={(event) => updateField("description", event.target.value)}
                placeholder="描述这个复合层剧本负责的顶层业务流程。"
                style={{ minHeight: 160 }}
              />
            </label>

            <div className="settings-field settings-field--full">
              <div className="workspace-panel__header">
                <div>
                  <strong>剧本节点</strong>
                  <span>支持 composite、capability、human_approval 三类节点。</span>
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
                        <span>{node.id || "未命名节点"}</span>
                      </div>
                      <em>{node.type}</em>
                    </div>
                    <div className="settings-form-grid">
                      <label className="settings-field">
                        <span>节点 ID</span>
                        <input value={node.id} onChange={(event) => updateNode(index, { id: event.target.value })} />
                      </label>
                      <label className="settings-field">
                        <span>节点类型</span>
                        <select
                          value={node.type}
                          onChange={(event) =>
                            updateNode(index, {
                              type: event.target.value as GraphNodeDefinition["type"],
                              capability_id: "",
                              composite_id: "",
                              approval_label: "",
                            })
                          }
                        >
                          <option value="composite">composite</option>
                          <option value="capability">capability</option>
                          <option value="human_approval">human_approval</option>
                        </select>
                      </label>
                      {node.type === "composite" ? (
                        <label className="settings-field settings-field--full">
                          <span>分子层 composite</span>
                          <select value={node.composite_id} onChange={(event) => updateNode(index, { composite_id: event.target.value })}>
                            <option value="">请选择 composite</option>
                            {composites.map((composite) => (
                              <option key={composite.id} value={composite.id}>
                                {composite.name} · {composite.id}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : null}
                      {node.type === "capability" ? (
                        <label className="settings-field settings-field--full">
                          <span>原子能力</span>
                          <select value={node.capability_id} onChange={(event) => updateNode(index, { capability_id: event.target.value })}>
                            <option value="">请选择 capability</option>
                            {capabilities.map((capability) => (
                              <option key={capability.id} value={capability.id}>
                                {capability.name} · {capability.id}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : null}
                      {node.type === "human_approval" ? (
                        <label className="settings-field settings-field--full">
                          <span>审批标签</span>
                          <input
                            value={node.approval_label}
                            onChange={(event) => updateNode(index, { approval_label: event.target.value })}
                            placeholder="Review draft"
                          />
                        </label>
                      ) : null}
                      <label className="settings-field settings-field--full">
                        <span>节点 config JSON</span>
                        <textarea
                          value={node.config}
                          onChange={(event) => updateNode(index, { config: event.target.value })}
                          style={{ minHeight: 120, fontFamily: "Consolas, Monaco, monospace" }}
                        />
                      </label>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => removeNode(index)} disabled={form.nodes.length === 1}>
                        删除节点
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="settings-field settings-field--full">
              <div className="workspace-panel__header">
                <div>
                  <strong>边关系</strong>
                  <span>定义节点之间的有向流转，可为审批节点加 approve / reject 条件。</span>
                </div>
                <button type="button" className="settings-cta settings-cta--secondary" onClick={addEdge}>
                  添加边
                </button>
              </div>
              <div className="settings-provider-list">
                {form.edges.map((edge, index) => (
                  <article key={`${edge.source}-${edge.target}-${index}`} className="settings-provider-card">
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>边 {index + 1}</strong>
                        <span>{edge.source || "source"} → {edge.target || "target"}</span>
                      </div>
                      <em>{edge.condition || "default"}</em>
                    </div>
                    <div className="settings-form-grid">
                      <label className="settings-field">
                        <span>Source</span>
                        <select value={edge.source} onChange={(event) => updateEdge(index, { source: event.target.value })}>
                          <option value="">请选择 source</option>
                          {availableNodeIds.map((nodeId) => (
                            <option key={`source-${nodeId}`} value={nodeId}>
                              {nodeId}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="settings-field">
                        <span>Target</span>
                        <select value={edge.target} onChange={(event) => updateEdge(index, { target: event.target.value })}>
                          <option value="">请选择 target</option>
                          {availableNodeIds.map((nodeId) => (
                            <option key={`target-${nodeId}`} value={nodeId}>
                              {nodeId}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="settings-field settings-field--full">
                        <span>条件</span>
                        <input
                          value={edge.condition}
                          onChange={(event) => updateEdge(index, { condition: event.target.value })}
                          placeholder="approve / reject / 留空表示默认流转"
                        />
                      </label>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => removeEdge(index)}>
                        删除边
                      </button>
                    </div>
                  </article>
                ))}
                {!form.edges.length ? <p className="workspace-empty">还没有边关系，至少补一条主干流转。</p> : null}
              </div>
            </div>

            <div className="settings-form-actions settings-field--full">
              <button type="button" className="settings-cta settings-cta--primary" onClick={savePlaybook} disabled={isPending}>
                {isPending ? "处理中..." : selectedPlaybook ? "更新复合层剧本" : "创建复合层剧本"}
              </button>
              <button type="button" className="settings-cta settings-cta--secondary" onClick={runCompile} disabled={isPending}>
                {isPending ? "处理中..." : "编译检查"}
              </button>
              <button type="button" className="settings-cta settings-cta--secondary" onClick={removePlaybook} disabled={isPending || !selectedPlaybook}>
                删除当前剧本
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
              <strong>剧本摘要</strong>
              <span>{selectedPlaybook?.name ?? "新建复合层剧本"}</span>
            </div>
          </div>
          <div className="workspace-summary">
            <h3>一、顶层职责</h3>
            <p>复合层剧本负责把分子层 composite、人工审批节点和局部原子能力组合成真正可运行的业务流程。</p>
            <h3>二、配置重点</h3>
            <ul>
              <li>入口节点必须存在且可达</li>
              <li>审批节点必须同时定义 approve / reject 出口</li>
              <li>尽量避免孤立节点和无条件回路</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>编译结果</strong>
              <span>运行前先看结构是否自洽</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{selectedCompile ? (selectedCompile.ok ? "编译通过" : "存在问题") : "等待编译"}</h3>
            <p>{selectedCompile ? `errors: ${selectedCompile.errors.length} · warnings: ${selectedCompile.warnings.length}` : "点击编译检查查看结果。"}</p>
            <div className="settings-focus__tags">
              {(selectedCompile?.errors ?? []).slice(0, 3).map((item) => (
                <span key={`playbook-error-${item}`}>{item}</span>
              ))}
              {(selectedCompile?.warnings ?? []).slice(0, 3).map((item) => (
                <span key={`playbook-warning-${item}`}>{item}</span>
              ))}
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>节点池</strong>
              <span>当前可挂接的分子和原子</span>
            </div>
          </div>
          <div className="settings-capability-list">
            {composites.slice(0, 8).map((composite) => (
              <span key={composite.id}>{composite.name}</span>
            ))}
            {capabilities.slice(0, 6).map((capability) => (
              <span key={capability.id}>{capability.name}</span>
            ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>剧本拓扑可视化预览</strong>
              <span>全局画布预览入口、主链、审批分支与孤立点</span>
            </div>
          </div>
          {topologyCanvas.nodes.length ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div className="settings-focus__tags">
                <span>entry = 蓝色描边</span>
                <span>approval = 橙色</span>
                <span>capability = 绿色</span>
                <span>composite = 灰蓝</span>
              </div>
              <div
                style={{
                  overflow: "auto",
                  borderRadius: 20,
                  border: "1px solid rgba(33, 53, 88, 0.1)",
                  background:
                    "radial-gradient(circle at top left, rgba(79, 124, 255, 0.08), transparent 28%), linear-gradient(180deg, rgba(255,255,255,0.9), rgba(244,247,252,0.86))",
                  padding: 8,
                }}
              >
                <svg
                  viewBox={`0 0 ${topologyCanvas.width} ${topologyCanvas.height}`}
                  width="100%"
                  height={Math.max(320, Math.min(620, topologyCanvas.height))}
                  role="img"
                  aria-label="graph playbook topology canvas"
                >
                  <defs>
                    <marker id="topology-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(124, 134, 155, 0.9)" />
                    </marker>
                  </defs>

                  {topologyCanvas.edges.map((edge) => {
                    const startX = edge.source.x + edge.source.width;
                    const startY = edge.source.y + edge.source.height / 2;
                    const endX = edge.target.x;
                    const endY = edge.target.y + edge.target.height / 2;
                    const bendX = startX + Math.max(28, (endX - startX) / 2);
                    return (
                      <g key={edge.key}>
                        <path
                          d={`M ${startX} ${startY} C ${bendX} ${startY}, ${bendX} ${endY}, ${endX - 10} ${endY}`}
                          fill="none"
                          stroke="rgba(124, 134, 155, 0.72)"
                          strokeWidth="2"
                          markerEnd="url(#topology-arrow)"
                        />
                        <text
                          x={(startX + endX) / 2}
                          y={(startY + endY) / 2 - 8}
                          textAnchor="middle"
                          fontSize="11"
                          fill={edge.condition === "approve" ? "#1d8f73" : edge.condition === "reject" ? "#c4544d" : "#7c869b"}
                        >
                          {edge.condition || "default"}
                        </text>
                      </g>
                    );
                  })}

                  {topologyCanvas.nodes.map((node) => {
                    const accent = nodeAccent(node.type, node.isEntry);
                    return (
                      <g key={node.id}>
                        <rect
                          x={node.x}
                          y={node.y}
                          width={node.width}
                          height={node.height}
                          rx="20"
                          fill={accent.fill}
                          stroke={accent.stroke}
                          strokeWidth={node.isEntry ? 2.5 : 1.4}
                        />
                        <circle cx={node.x + 18} cy={node.y + 18} r="6" fill={accent.badge} />
                        <text x={node.x + 32} y={node.y + 22} fontSize="11" fill={accent.badge}>
                          {nodeTypeLabel(node.type)}
                        </text>
                        <text x={node.x + 16} y={node.y + 46} fontSize="14" fontWeight="700" fill="#22304a">
                          {node.title.length > 20 ? `${node.title.slice(0, 20)}...` : node.title}
                        </text>
                        <text x={node.x + 16} y={node.y + 66} fontSize="11.5" fill="#7c869b">
                          {node.subtitle.length > 22 ? `${node.subtitle.slice(0, 22)}...` : node.subtitle}
                        </text>
                        <text x={node.x + 16} y={node.y + 82} fontSize="11" fill="#7c869b">
                          {`${node.incomingCount} 入 · ${node.outgoing.length} 出${node.isEntry ? " · entry" : ""}`}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
              <div className="settings-focus__tags">
                {topologyPreview.map((node) => (
                  <span key={`legend-${node.id || node.title}`}>
                    {node.title}: {node.outgoing.length ? node.outgoing.map((edge) => edge.target || "未指向").join(" / ") : "无下游"}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="workspace-empty">先添加节点后，这里会生成剧本拓扑预览。</p>
          )}
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>结构提示</strong>
              <span>保存前先扫一眼常见缺口</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{validationHints.length ? "发现待补项" : "结构看起来完整"}</h3>
            <p>{validationHints.length ? `当前有 ${validationHints.length} 条界面侧提示。` : "入口节点、边关系和审批出口暂未发现明显缺口。"}</p>
            <div className="settings-focus__tags">
              {(validationHints.length ? validationHints : ["可继续保存并执行编译检查。"]).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </div>
        </section>
      </aside>
    </section>
  );
}
