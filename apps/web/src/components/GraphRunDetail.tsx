"use client";

import { useEffect, useState } from "react";

import type { GraphPlaybookDefinition, GraphRun, GraphRunEvent } from "@/lib/api";
import { getGraphRunEventsUrl } from "@/lib/api";

import { GraphApprovalQueue } from "@/components/GraphApprovalQueue";
import { GraphStatusBadge } from "@/components/GraphStatusBadge";

type GraphRunDetailProps = {
  initialRun: GraphRun | null;
  playbooks: GraphPlaybookDefinition[];
  selectedNodeId?: string | null;
};

export function GraphRunDetail({ initialRun, playbooks, selectedNodeId }: GraphRunDetailProps) {
  const [run, setRun] = useState<GraphRun | null>(initialRun);
  const playbookName = playbooks.find((item) => item.id === run?.graph_playbook_id)?.name ?? run?.graph_playbook_id;
  const selectedNodeState = run?.node_states.find((nodeState) => nodeState.node_id === selectedNodeId) ?? null;

  useEffect(() => {
    setRun(initialRun);
  }, [initialRun]);

  useEffect(() => {
    if (!run?.id) {
      return;
    }
    const eventSource = new EventSource(getGraphRunEventsUrl(run.id));
    const applyEvent = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as GraphRunEvent;
        if (parsed.event_type === "snapshot") {
          setRun(parsed.payload as unknown as GraphRun);
        }
      } catch {
        return;
      }
    };
    eventSource.onmessage = applyEvent;
    eventSource.addEventListener("snapshot", applyEvent as EventListener);
    eventSource.addEventListener("run_updated", applyEvent as EventListener);
    eventSource.addEventListener("approval_recorded", applyEvent as EventListener);
    eventSource.addEventListener("approval_rejected", applyEvent as EventListener);
    return () => {
      eventSource.close();
    };
  }, [run?.id]);

  if (!run) {
    return (
      <aside className="workspace-rightbar">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>运行详情</strong>
              <span>等待运行</span>
            </div>
          </div>
          <p className="muted">选择或启动一个 Graph Playbook 运行后，这里会展示节点级执行信息和审批动作。</p>
        </section>
      </aside>
    );
  }

  return (
    <aside className="workspace-rightbar">
      <section className="workspace-panel workspace-panel--summary">
        <div className="workspace-panel__header">
          <div>
            <strong>运行详情</strong>
            <span>{playbookName}</span>
          </div>
          <GraphStatusBadge status={run.status} />
        </div>
        <div className="settings-focus">
          <h3>{run.id}</h3>
          <p>当前节点：{run.current_node_id ?? "completed"}。这个视图聚合了运行状态、节点输出和审批队列。</p>
          <div className="settings-focus__tags">
            <span>{run.graph_playbook_id}</span>
            <span>{run.node_states.length} 个节点状态</span>
            <span>{run.approvals.length} 个审批记录</span>
          </div>
        </div>
      </section>

      <section className="workspace-panel">
        <div className="workspace-panel__header">
          <div>
            <strong>{selectedNodeState ? "节点运行详情" : "节点状态"}</strong>
            <span>{selectedNodeState ? selectedNodeState.node_id : "按运行快照展示"}</span>
          </div>
        </div>
        <div className="settings-provider-list">
          {(selectedNodeState ? [selectedNodeState] : run.node_states).map((nodeState) => (
            <article key={nodeState.node_id} className="settings-provider-card">
              <div className="settings-provider-card__head">
                <div>
                  <strong>{nodeState.node_id}</strong>
                  <span>尝试次数：{nodeState.attempts}</span>
                </div>
                <GraphStatusBadge status={nodeState.status} />
              </div>
              {nodeState.error ? <p className="settings-agent-card__description">{nodeState.error}</p> : null}
              <div className="settings-response-block">
                <span>输出</span>
                <code>{JSON.stringify(nodeState.output, null, 2)}</code>
              </div>
            </article>
          ))}
        </div>
      </section>

      <GraphApprovalQueue run={run} onRunUpdate={setRun} />
    </aside>
  );
}
