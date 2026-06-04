"use client";

import { useMemo, useState } from "react";

import { ObservabilitySessionList } from "@/components/ObservabilitySessionList";
import type {
  ObservabilityEventRecord,
  ObservabilityMetrics,
  ObservabilitySessionSummary,
  ObservabilityTaskRecord,
  ObservabilityTimelineEntry,
} from "@/lib/api";

type ObservabilitySessionDetailProps = {
  sessionId: string;
  sessions: ObservabilitySessionSummary[];
  summary: ObservabilitySessionSummary;
  timeline: ObservabilityTimelineEntry[];
  tasks: ObservabilityTaskRecord[];
  metrics: ObservabilityMetrics;
  events: ObservabilityEventRecord[];
};

type TraceRow = {
  id: string;
  sequence: number;
  title: string;
  summary: string;
  timestamp: string;
  eventType: string;
  status: "running" | "success" | "error" | "info";
  laneLabel: string;
  offsetPercent: number;
  widthPercent: number;
  detailPayload: Record<string, unknown>;
  runtimeId?: string | null;
  turn?: number | null;
};

function formatDateTime(value?: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString("zh-CN");
}

function formatDuration(ms: number) {
  if (!ms) {
    return "0 ms";
  }
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(ms >= 10_000 ? 0 : 1)} s`;
  }
  return `${Math.round(ms)} ms`;
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatMaybeNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value >= 1000 ? value.toLocaleString("zh-CN") : String(value);
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (value == null || value === "") {
    return "n/a";
  }
  return String(value);
}

function computeTaskDepths(tasks: ObservabilityTaskRecord[]) {
  const taskMap = new Map(tasks.map((task) => [task.task_id, task]));
  const depthMap = new Map<string, number>();

  const visit = (taskId: string): number => {
    const cached = depthMap.get(taskId);
    if (cached != null) {
      return cached;
    }
    const task = taskMap.get(taskId);
    if (!task?.parent_task_id || !taskMap.has(task.parent_task_id)) {
      depthMap.set(taskId, 0);
      return 0;
    }
    const depth = visit(task.parent_task_id) + 1;
    depthMap.set(taskId, depth);
    return depth;
  };

  tasks.forEach((task) => visit(task.task_id));
  return depthMap;
}

function buildTraceRows(
  timeline: ObservabilityTimelineEntry[],
  events: ObservabilityEventRecord[],
  metrics: ObservabilityMetrics,
) {
  const eventMap = new Map(events.map((event) => [event.event_id, event]));
  const total = Math.max(timeline.length, 1);

  return timeline.map((entry, index) => {
    const event = eventMap.get(entry.event_id);
    const payload = event?.payload ?? entry.payload ?? {};
    const rawDuration =
      typeof payload.duration_ms === "number"
        ? payload.duration_ms
        : typeof payload.elapsed_ms === "number"
          ? payload.elapsed_ms
          : entry.event_type.includes("tool")
            ? metrics.avg_tool_duration_ms
            : entry.event_type.includes("model")
              ? metrics.avg_model_duration_ms
              : 260;
    const widthPercent = Math.max(10, Math.min(76, rawDuration > 0 ? rawDuration / 80 : 18));
    const offsetPercent = total === 1 ? 4 : (index / (total - 1)) * 50 + (index % 3) * 2;

    return {
      id: entry.event_id,
      sequence: entry.sequence,
      title: entry.title,
      summary: entry.summary,
      timestamp: entry.timestamp,
      eventType: entry.event_type,
      status: entry.status,
      laneLabel: entry.event_type.replaceAll("_", " "),
      offsetPercent,
      widthPercent,
      detailPayload: payload,
      runtimeId: event?.runtime_id,
      turn: event?.turn,
    } satisfies TraceRow;
  });
}

function statusClassName(status: TraceRow["status"]) {
  switch (status) {
    case "success":
      return "observability-trace-row--success";
    case "error":
      return "observability-trace-row--error";
    case "running":
      return "observability-trace-row--running";
    default:
      return "observability-trace-row--info";
  }
}

export function ObservabilitySessionDetail({
  sessionId,
  sessions,
  summary,
  timeline,
  tasks,
  metrics,
  events,
}: ObservabilitySessionDetailProps) {
  const traceRows = useMemo(() => buildTraceRows(timeline, events, metrics), [events, metrics, timeline]);
  const [selectedTraceId, setSelectedTraceId] = useState(traceRows[0]?.id ?? "");
  const [isTaskTreeCollapsed, setIsTaskTreeCollapsed] = useState(false);

  const eventMap = useMemo(() => new Map(events.map((event) => [event.event_id, event])), [events]);
  const taskDepthMap = useMemo(() => computeTaskDepths(tasks), [tasks]);
  const anomalyEvents = useMemo(
    () => events.filter((event) => event.event_type === "anomaly_detected"),
    [events],
  );
  const selectedTrace =
    traceRows.find((row) => row.id === selectedTraceId) ??
    traceRows[0] ?? {
      id: "",
      sequence: 0,
      title: "no trace",
      summary: "当前还没有时间线事件。",
      timestamp: summary.last_updated_at ?? new Date().toISOString(),
      eventType: "info",
      status: "info",
      laneLabel: "info",
      offsetPercent: 0,
      widthPercent: 20,
      detailPayload: {},
      runtimeId: null,
      turn: null,
    };
  const selectedEvent = eventMap.get(selectedTrace.id);
  const selectedTask =
    tasks.find((task) => task.source_event_id === selectedTrace.id) ??
    tasks.find((task) => selectedTrace.runtimeId && task.source_event_id == null && task.title === selectedTrace.title) ??
    null;

  const inspectorFields = [
    ["event_type", selectedTrace.eventType],
    ["sequence", selectedTrace.sequence],
    ["runtime_id", selectedTrace.runtimeId],
    ["turn", selectedTrace.turn],
    ["task_kind", selectedTask?.kind],
    ["task_status", selectedTask?.status],
    ["timestamp", formatDateTime(selectedTrace.timestamp)],
    ["tool_call_id", selectedTrace.detailPayload.tool_call_id],
    ["tool_name", selectedTrace.detailPayload.tool_name],
    ["provider_id", selectedTrace.detailPayload.provider_id],
    ["model", selectedTrace.detailPayload.model],
    ["ok", selectedTrace.detailPayload.ok],
  ].filter(
    (field): field is [string, unknown] => field[1] !== undefined && field[1] !== null && field[1] !== "",
  );

  return (
    <main className="observability-shell">
      <aside className="observability-sidebar">
        <section className="observability-sidebar__panel">
          <div className="observability-sidebar__header">
            <div>
              <span className="observability-kicker">Trace Index</span>
              <strong>Review Sessions</strong>
            </div>
            <span>{sessions.length}</span>
          </div>
          <ObservabilitySessionList sessions={sessions} selectedSessionId={sessionId} />
        </section>
      </aside>

      <section className="observability-main">
        <header className="observability-header">
          <div>
            <span className="observability-kicker">Observability / Timeline</span>
            <h1>{sessionId}</h1>
            <p>
              {summary.playbook_id ?? "review session"} · {summary.status ?? "unknown"} ·{" "}
              {formatDateTime(summary.last_updated_at)}
            </p>
          </div>
          <div className="observability-header__badges">
            <span className="observability-pill">{summary.evaluation_grade ?? "pending"}</span>
            <span className="observability-pill observability-pill--ghost">{summary.provider_id ?? "local trace"}</span>
          </div>
        </header>

        <section className="observability-metrics">
          <article className="observability-metric-card">
            <span>Session Health</span>
            <strong>{summary.anomaly_count ? "Watch" : "Stable"}</strong>
            <small>{summary.anomaly_count} anomaly events</small>
          </article>
          <article className="observability-metric-card">
            <span>Turns / Tools</span>
            <strong>
              {metrics.llm_turn_count} / {metrics.tool_call_count}
            </strong>
            <small>{metrics.tool_error_count} tool failures</small>
          </article>
          <article className="observability-metric-card">
            <span>Latency</span>
            <strong>{formatDuration(metrics.session_duration_ms)}</strong>
            <small>model avg {formatDuration(metrics.avg_model_duration_ms)}</small>
          </article>
          <article className="observability-metric-card">
            <span>Context Load</span>
            <strong>{metrics.max_context_usage_percent}%</strong>
            <small>{metrics.estimated_total_tokens.toLocaleString("zh-CN")} total tokens</small>
          </article>
        </section>

        <section className="observability-stage">
          <div className="observability-stage__header">
            <div>
              <span className="observability-kicker">Trace Timeline</span>
              <strong>事件树与运行轨迹</strong>
            </div>
            <span>{traceRows.length} rows</span>
          </div>

          <div className="observability-trace-table">
            <div className="observability-trace-table__head">
              <span>Step</span>
              <span>Lane</span>
              <span>Timeline</span>
            </div>
            <div className="observability-trace-table__body">
              {traceRows.length ? (
                traceRows.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    className={`observability-trace-row ${statusClassName(row.status)}${
                      row.id === selectedTrace.id ? " observability-trace-row--selected" : ""
                    }`}
                    onClick={() => setSelectedTraceId(row.id)}
                  >
                    <div className="observability-trace-row__step">
                      <strong>#{row.sequence}</strong>
                      <small>{formatDateTime(row.timestamp)}</small>
                    </div>
                    <div className="observability-trace-row__lane">
                      <span className="observability-pill observability-pill--ghost">{row.status}</span>
                      <strong>{row.title}</strong>
                      <small>{row.summary}</small>
                    </div>
                    <div className="observability-trace-row__bar">
                      <div className="observability-trace-row__track" />
                      <div
                        className="observability-trace-row__fill"
                        style={{
                          left: `${row.offsetPercent}%`,
                          width: `${row.widthPercent}%`,
                        }}
                      />
                      <span className="observability-trace-row__label">{row.laneLabel}</span>
                    </div>
                  </button>
                ))
              ) : (
                <p className="workspace-empty">当前会话还没有时间线事件。</p>
              )}
            </div>
          </div>
        </section>

        <section className="observability-lower-grid">
          <article className="observability-panel">
            <div className="observability-panel__header">
              <div>
                <span className="observability-kicker">Task Tree</span>
                <strong>执行节点</strong>
              </div>
              <div className="observability-panel__actions">
                <span>{tasks.length}</span>
                <button
                  type="button"
                  className="observability-toggle-button"
                  onClick={() => setIsTaskTreeCollapsed((value) => !value)}
                  aria-expanded={!isTaskTreeCollapsed}
                >
                  {isTaskTreeCollapsed ? "展开" : "收起"}
                </button>
              </div>
            </div>
            {isTaskTreeCollapsed ? (
              <p className="workspace-empty">执行节点栏已收起，点击“展开”可恢复查看。</p>
            ) : (
              <div className="observability-task-list">
                {tasks.map((task) => (
                  <div
                    key={task.task_id}
                    className={`observability-task-row${
                      selectedTask?.task_id === task.task_id ? " observability-task-row--selected" : ""
                    }`}
                    style={{ paddingLeft: `${16 + (taskDepthMap.get(task.task_id) ?? 0) * 20}px` }}
                  >
                    <span className="observability-task-row__kind">{task.kind}</span>
                    <div>
                      <strong>{task.title}</strong>
                      <small>
                        {task.status} · {task.summary ?? "no summary"}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="observability-panel">
            <div className="observability-panel__header">
              <div>
                <span className="observability-kicker">Signals</span>
                <strong>异常与结论</strong>
              </div>
              <span>{anomalyEvents.length}</span>
            </div>
            <div className="observability-signal-list">
              <div className="observability-signal-card">
                <span>Evaluation</span>
                <strong>{summary.evaluation_grade ?? "pending"}</strong>
                <small>resume {metrics.resume_count} · tool error {formatPercent(metrics.tool_error_rate)}</small>
              </div>
              {anomalyEvents.length ? (
                anomalyEvents.map((event) => (
                  <div key={event.event_id} className="observability-signal-card observability-signal-card--alert">
                    <span>{String(event.payload.severity ?? "anomaly")}</span>
                    <strong>{String(event.payload.title ?? event.payload.code ?? "anomaly")}</strong>
                    <small>{String(event.payload.summary ?? "")}</small>
                  </div>
                ))
              ) : (
                <div className="observability-signal-card">
                  <span>Runtime</span>
                  <strong>No anomaly</strong>
                  <small>当前没有检测到运行期异常。</small>
                </div>
              )}
            </div>
          </article>
        </section>
      </section>

      <aside className="observability-inspector">
        <section className="observability-inspector__panel">
          <div className="observability-sidebar__header">
            <div>
              <span className="observability-kicker">Inspector</span>
              <strong>{selectedTrace.title}</strong>
            </div>
            <span className="observability-pill">{selectedTrace.status}</span>
          </div>

          <div className="observability-inspector__block">
            <p>{selectedTrace.summary}</p>
            <div className="observability-inspector__grid">
              {inspectorFields.map(([label, value]) => (
                <div key={label} className="observability-inspector__field">
                  <span>{label}</span>
                  <strong>{formatMaybeNumber(value)}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="observability-inspector__block">
            <div className="observability-panel__header">
              <strong>Payload</strong>
              <span>{selectedEvent?.span_id ?? "json"}</span>
            </div>
            <pre>{JSON.stringify(selectedTrace.detailPayload, null, 2)}</pre>
          </div>

          <div className="observability-inspector__block">
            <div className="observability-panel__header">
              <strong>Raw Event</strong>
              <span>{selectedEvent?.event_id ?? "n/a"}</span>
            </div>
            <pre>{JSON.stringify(selectedEvent ?? null, null, 2)}</pre>
          </div>
        </section>
      </aside>
    </main>
  );
}
