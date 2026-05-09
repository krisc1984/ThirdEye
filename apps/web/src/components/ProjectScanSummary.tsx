import type { ProjectScanSummary } from "@/lib/api";

type ProjectScanSummaryProps = {
  summary: ProjectScanSummary;
};

function renderPairs(record: Record<string, number>) {
  const entries = Object.entries(record);
  if (!entries.length) {
    return <p className="muted">None detected.</p>;
  }

  return (
    <ul className="token-list">
      {entries.map(([key, value]) => (
        <li key={key} className="token-list__item">
          <span>{key}</span>
          <strong>{value}</strong>
        </li>
      ))}
    </ul>
  );
}

function renderList(items: string[]) {
  if (!items.length) {
    return <p className="muted">None.</p>;
  }

  return (
    <ul className="plain-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ProjectScanSummary({ summary }: ProjectScanSummaryProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Scan Summary</p>
          <h2>Project snapshot</h2>
        </div>
        <p className="muted">{summary.root_path}</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span>Total files</span>
          <strong>{summary.total_files}</strong>
        </div>
        <div className="stat-card">
          <span>Scanned</span>
          <strong>{summary.scanned_files}</strong>
        </div>
        <div className="stat-card">
          <span>Skipped</span>
          <strong>{summary.skipped_files}</strong>
        </div>
      </div>

      <div className="info-grid">
        <article className="subpanel">
          <h3>Languages</h3>
          {renderPairs(summary.languages)}
        </article>
        <article className="subpanel">
          <h3>Docs</h3>
          {renderList(summary.docs)}
        </article>
        <article className="subpanel">
          <h3>Tests</h3>
          {renderList(summary.tests)}
        </article>
        <article className="subpanel">
          <h3>Config files</h3>
          {renderList(summary.config_files)}
        </article>
        <article className="subpanel">
          <h3>Entrypoints</h3>
          {renderList(summary.entrypoint_candidates)}
        </article>
        <article className="subpanel">
          <h3>Warnings</h3>
          {renderList(summary.sensitive_warnings)}
        </article>
      </div>
    </section>
  );
}
