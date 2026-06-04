 "use client";

import type { GraphPlaybookDefinition, GraphRun } from "@/lib/api";

import { GraphStatusBadge } from "@/components/GraphStatusBadge";

type GraphRunListProps = {
  runs: GraphRun[];
  playbooks: GraphPlaybookDefinition[];
  selectedRunId?: string | null;
  onSelectRun?: (run: GraphRun) => void;
};

export function GraphRunList({ runs, playbooks, selectedRunId, onSelectRun }: GraphRunListProps) {
  const playbookNames = new Map(playbooks.map((playbook) => [playbook.id, playbook.name]));

  if (!runs.length) {
    return (
      <p className="workspace-empty">还没有图谱运行记录。可以从上方直接启动 run。</p>
    );
  }

  return (
    <div className="settings-provider-list">
      {runs.map((run) => (
        <button
          key={run.id}
          type="button"
          className={`settings-provider-card ${selectedRunId === run.id ? "settings-provider-card--active" : ""}`}
          style={{ textAlign: "left", cursor: onSelectRun ? "pointer" : "default" }}
          onClick={() => onSelectRun?.(run)}
        >
          <div className="settings-provider-card__head">
            <div>
              <strong>{playbookNames.get(run.graph_playbook_id) ?? run.graph_playbook_id}</strong>
              <span>{run.id}</span>
            </div>
            <GraphStatusBadge status={run.status} />
          </div>
          <div className="settings-provider-card__meta">
            <span>{run.current_node_id ?? "completed"}</span>
            <span>{run.approvals.filter((item) => item.status === "pending").length} 待审批</span>
          </div>
        </button>
      ))}
    </div>
  );
}
