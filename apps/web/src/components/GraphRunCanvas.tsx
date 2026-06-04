"use client";

import "@xyflow/react/dist/style.css";

import { useMemo } from "react";

import type { GraphPlaybookDefinition, GraphRun } from "@/lib/api";

import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

type GraphRunCanvasProps = {
  run: GraphRun | null;
  playbook: GraphPlaybookDefinition | null;
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string | null) => void;
};

type CanvasNodeMeta = {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  state: string;
  isCurrent: boolean;
};

const toneByStatus: Record<string, { fill: string; stroke: string; text: string }> = {
  pending: { fill: "#f8f5ef", stroke: "#c9b79f", text: "#7d6d5c" },
  running: { fill: "#ebf1ff", stroke: "#4f7cff", text: "#213558" },
  waiting_for_human: { fill: "#fff1e6", stroke: "#ff9b52", text: "#8c4e1f" },
  succeeded: { fill: "#e8f8f3", stroke: "#42b59a", text: "#1d8f73" },
  failed: { fill: "#fff0ef", stroke: "#d46a62", text: "#a23f37" },
  skipped: { fill: "#f2f4f7", stroke: "#a0aec0", text: "#718096" },
};

function buildSubtitle(playbook: GraphPlaybookDefinition, nodeId: string) {
  const node = playbook.nodes.find((item) => item.id === nodeId);
  if (!node) {
    return "未找到节点定义";
  }
  if (node.type === "composite") {
    return node.composite_id ?? "未绑定 composite";
  }
  if (node.type === "capability") {
    return node.capability_id ?? "未绑定 capability";
  }
  return node.approval_label ?? "待人工审批";
}

function buildCanvasLayout(playbook: GraphPlaybookDefinition) {
  const nodeIds = playbook.nodes.map((node) => node.id);
  const adjacency = new Map<string, string[]>();
  const indegree = new Map<string, number>();

  for (const nodeId of nodeIds) {
    adjacency.set(nodeId, []);
    indegree.set(nodeId, 0);
  }

  for (const edge of playbook.edges) {
    adjacency.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  }

  const queue: string[] = [];
  const levels = new Map<string, number>();
  if (playbook.entry_node_id && adjacency.has(playbook.entry_node_id)) {
    queue.push(playbook.entry_node_id);
    levels.set(playbook.entry_node_id, 0);
  }
  for (const nodeId of nodeIds) {
    if ((indegree.get(nodeId) ?? 0) === 0 && !levels.has(nodeId)) {
      queue.push(nodeId);
      levels.set(nodeId, nodeId === playbook.entry_node_id ? 0 : 1);
    }
  }

  while (queue.length) {
    const current = queue.shift();
    if (!current) {
      continue;
    }
    const currentLevel = levels.get(current) ?? 0;
    for (const next of adjacency.get(current) ?? []) {
      const nextLevel = currentLevel + 1;
      if (!levels.has(next) || nextLevel > (levels.get(next) ?? 0)) {
        levels.set(next, nextLevel);
        queue.push(next);
      }
    }
  }

  const columns = new Map<number, string[]>();
  for (const nodeId of nodeIds) {
    const level = levels.get(nodeId) ?? 0;
    columns.set(level, [...(columns.get(level) ?? []), nodeId]);
  }

  const cardWidth = 220;
  const cardHeight = 92;
  const gapX = 100;
  const gapY = 48;
  const padding = 40;

  const positions = new Map<string, { x: number; y: number }>();
  [...columns.entries()]
    .sort((left, right) => left[0] - right[0])
    .forEach(([column, ids]) => {
      ids.forEach((id, row) => {
        positions.set(id, {
          x: padding + column * (cardWidth + gapX),
          y: padding + row * (cardHeight + gapY),
        });
      });
    });

  return { positions, cardWidth, cardHeight };
}

export function GraphRunCanvas({ run, playbook, selectedNodeId, onSelectNode }: GraphRunCanvasProps) {
  const flow = useMemo(() => {
    if (!run || !playbook) {
      return { nodes: [] as Node<CanvasNodeMeta>[], edges: [] as Edge[] };
    }

    const stateMap = new Map(run.node_states.map((nodeState) => [nodeState.node_id, nodeState] as const));
    const { positions } = buildCanvasLayout(playbook);

    const nodes: Node<CanvasNodeMeta>[] = playbook.nodes.map((node) => {
      const state = stateMap.get(node.id)?.status ?? "pending";
      const tone = toneByStatus[state] ?? toneByStatus.pending;
      const isSelected = selectedNodeId === node.id;
      const isCurrent = run.current_node_id === node.id;
      return {
        id: node.id,
        position: positions.get(node.id) ?? { x: 0, y: 0 },
        draggable: false,
        data: {
          id: node.id,
          type: node.type,
          title: node.id,
          subtitle: buildSubtitle(playbook, node.id),
          state,
          isCurrent,
        },
        style: {
          width: 220,
          minHeight: 92,
          borderRadius: 22,
          padding: "14px 16px",
          border: `${isSelected ? 3 : isCurrent ? 2.5 : 1.5}px solid ${tone.stroke}`,
          background: tone.fill,
          color: tone.text,
          boxShadow: isCurrent ? "0 0 0 6px rgba(79, 124, 255, 0.12)" : "0 12px 24px rgba(54, 72, 98, 0.08)",
          fontSize: 12,
          lineHeight: 1.4,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });

    const edges: Edge[] = playbook.edges.map((edge, index) => ({
      id: `${edge.source}-${edge.target}-${edge.condition ?? "default"}-${index}`,
      source: edge.source,
      target: edge.target,
      label: edge.condition ?? undefined,
      type: "smoothstep",
      animated: run.current_node_id === edge.source,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#94a3b8",
      },
      style: {
        stroke: "#94a3b8",
        strokeWidth: edge.condition ? 2.2 : 1.6,
      },
      labelStyle: {
        fill: "#7c869b",
        fontSize: 11,
      },
    }));

    return { nodes, edges };
  }, [playbook, run, selectedNodeId]);

  if (!run || !playbook) {
    return (
      <section className="workspace-panel" style={{ minHeight: 560 }}>
        <div className="workspace-panel__header">
          <div>
            <strong>运行画布</strong>
            <span>等待选择运行</span>
          </div>
        </div>
        <p className="workspace-empty">启动或选择一个 run 后，这里会展示基于 playbook 骨架的无限画布。</p>
      </section>
    );
  }

  return (
    <section className="workspace-panel" style={{ minHeight: 560, padding: 0, overflow: "hidden" }}>
      <div className="workspace-panel__header" style={{ padding: "18px 20px 0" }}>
        <div>
          <strong>运行画布</strong>
          <span>{playbook.name} · 结构骨架 + 运行染色</span>
        </div>
      </div>
      <div style={{ height: 560, width: "100%" }}>
        <ReactFlow
          nodes={flow.nodes}
          edges={flow.edges}
          fitView
          minZoom={0.4}
          maxZoom={1.8}
          nodesConnectable={false}
          nodesDraggable={false}
          elementsSelectable
          onNodeClick={(_, node) => onSelectNode?.(node.id)}
          onPaneClick={() => onSelectNode?.(null)}
        >
          <Background gap={24} size={1} color="rgba(124, 134, 155, 0.18)" />
          <MiniMap
            pannable
            zoomable
            style={{ background: "rgba(255,255,255,0.88)", border: "1px solid rgba(33, 53, 88, 0.1)" }}
            nodeColor={(node) => toneByStatus[(node.data as CanvasNodeMeta | undefined)?.state ?? "pending"]?.stroke ?? "#94a3b8"}
          />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  );
}
