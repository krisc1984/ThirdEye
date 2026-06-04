import Link from "next/link";

import type { ObservabilitySessionSummary } from "@/lib/api";

type ObservabilitySessionListProps = {
  sessions: ObservabilitySessionSummary[];
  selectedSessionId?: string;
};

function getStatusLabel(session: ObservabilitySessionSummary) {
  return session.status ?? session.evaluation_grade ?? "unknown";
}

function formatTokenCount(value: number) {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}k`;
  }
  return String(value);
}

export function ObservabilitySessionList({
  sessions,
  selectedSessionId,
}: ObservabilitySessionListProps) {
  if (!sessions.length) {
    return <p className="workspace-empty">还没有可观察性会话数据。</p>;
  }

  return (
    <div className="observability-session-list">
      {sessions.map((session) => {
        const active = session.session_id === selectedSessionId;
        const status = getStatusLabel(session);

        return (
          <Link
            key={session.session_id}
            href={`/observability/sessions/${encodeURIComponent(session.session_id)}`}
            className={`observability-session-card${active ? " observability-session-card--active" : ""}`}
          >
            <div className="observability-session-card__meta">
              <span className="observability-pill observability-pill--ghost">{status}</span>
              <span className="observability-session-card__time">
                {session.last_updated_at ? new Date(session.last_updated_at).toLocaleString("zh-CN") : "waiting"}
              </span>
            </div>
            <strong>{session.session_id}</strong>
            <p>{session.playbook_id ?? "review session"}</p>
            <div className="observability-session-card__stats">
              <span>{session.metrics.llm_turn_count} turns</span>
              <span>{session.metrics.tool_call_count} tools</span>
              <span>{formatTokenCount(session.metrics.estimated_total_tokens)} tokens</span>
            </div>
            <div className="observability-session-card__footer">
              <span className="observability-pill">{session.evaluation_grade ?? "pending"}</span>
              <span className="observability-session-card__anomaly">
                {session.anomaly_count ? `${session.anomaly_count} anomaly` : "clean"}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
