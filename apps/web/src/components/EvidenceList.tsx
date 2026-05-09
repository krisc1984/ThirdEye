import type { EvidenceItem } from "@/lib/api";

type EvidenceListProps = {
  evidence: EvidenceItem[];
};

export function EvidenceList({ evidence }: EvidenceListProps) {
  if (!evidence.length) {
    return <p className="muted">No evidence found.</p>;
  }

  return (
    <div className="evidence-list">
      {evidence.map((item) => (
        <article key={item.id} className="evidence-card">
          <div className="evidence-card__meta">
            <span>{item.source_type}</span>
            <span>{item.evidence_level}</span>
          </div>
          <h3>{item.path}</h3>
          {item.symbol ? <p className="muted">{item.symbol}</p> : null}
          <p>{item.summary}</p>
          <code>{item.id}</code>
        </article>
      ))}
    </div>
  );
}
