"use client";

type ExecutionDetailsProps = {
  title?: string;
  executionMode: "deterministic" | "llm";
  resolvedProviderId?: string | null;
  executionNote?: string | null;
  requestProviderId?: string | null;
};

function describeExecutionMode(executionMode: "deterministic" | "llm") {
  return executionMode === "llm" ? "LLM API executed" : "Deterministic fallback executed";
}

export function ExecutionDetails({
  title = "Execution details",
  executionMode,
  resolvedProviderId,
  executionNote,
  requestProviderId
}: ExecutionDetailsProps) {
  const statusTone = executionMode === "llm" ? "status--success" : "status--warning";

  return (
    <details className="debug-details">
      <summary className="debug-details__summary">
        <span>{title}</span>
        <span className={`status-chip ${statusTone}`}>{describeExecutionMode(executionMode)}</span>
      </summary>

      <div className="debug-grid">
        <article className="subpanel">
          <h3>Execution mode</h3>
          <p>{executionMode}</p>
        </article>
        <article className="subpanel">
          <h3>Requested provider</h3>
          <p>{requestProviderId ?? "not specified"}</p>
        </article>
        <article className="subpanel">
          <h3>Resolved provider</h3>
          <p>{resolvedProviderId ?? "fallback"}</p>
        </article>
        <article className="subpanel">
          <h3>Execution note</h3>
          <p>{executionNote ?? "No additional note."}</p>
        </article>
      </div>
    </details>
  );
}
