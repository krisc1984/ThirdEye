"use client";

import { useState, useTransition } from "react";

import type { GraphApprovalDecision, GraphRun } from "@/lib/api";
import { submitGraphApproval } from "@/lib/api";

import { GraphStatusBadge } from "@/components/GraphStatusBadge";

type GraphApprovalQueueProps = {
  run: GraphRun;
  onRunUpdate?: (run: GraphRun) => void;
};

export function GraphApprovalQueue({ run, onRunUpdate }: GraphApprovalQueueProps) {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const pendingApprovals = run.approvals.filter((approval) => approval.status === "pending");

  function handleDecision(approval: GraphApprovalDecision, approved: boolean) {
    setError(null);
    startTransition(async () => {
      try {
        const updated = await submitGraphApproval(run.id, approval.approval_id, {
          approved,
          decided_by: "web-cockpit"
        });
        onRunUpdate?.(updated);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "提交审批失败。");
      }
    });
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-panel__header">
        <div>
          <strong>审批队列</strong>
          <span>{pendingApprovals.length ? `${pendingApprovals.length} 条待处理` : "当前为空"}</span>
        </div>
      </div>
      <div className="settings-provider-list">
        {pendingApprovals.length ? (
          pendingApprovals.map((approval) => (
            <article key={approval.approval_id} className="settings-provider-card">
              <div className="settings-provider-card__head">
                <div>
                  <strong>{approval.node_id}</strong>
                  <span>{approval.approval_id}</span>
                </div>
                <GraphStatusBadge status={approval.status} />
              </div>
              <div className="settings-provider-card__actions">
                <button type="button" onClick={() => handleDecision(approval, true)} disabled={isPending}>
                  通过
                </button>
                <button type="button" onClick={() => handleDecision(approval, false)} disabled={isPending}>
                  驳回
                </button>
              </div>
            </article>
          ))
        ) : (
          <p className="muted">当前没有待处理的人审节点。</p>
        )}
      </div>
      {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
    </section>
  );
}
