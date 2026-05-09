"use client";

import { useMemo, useState } from "react";

import type { EvidenceItem } from "@/lib/api";

type EvidencePanelProps = {
  evidence: EvidenceItem[];
  selectedEvidenceIds: string[];
};

export function EvidencePanel({ evidence, selectedEvidenceIds }: EvidencePanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(selectedEvidenceIds[0] ?? null);

  const evidenceMap = useMemo(() => new Map(evidence.map((item) => [item.id, item])), [evidence]);
  const selectedEvidence = selectedEvidenceIds
    .map((id) => evidenceMap.get(id))
    .filter((item): item is EvidenceItem => Boolean(item));

  if (!selectedEvidence.length) {
    return (
      <aside className="subpanel">
        <h3>Evidence panel</h3>
        <p className="muted">Select a finding with linked evidence to inspect its source summary.</p>
      </aside>
    );
  }

  const active = selectedEvidence.find((item) => item.id === expandedId) ?? selectedEvidence[0];

  return (
    <aside className="subpanel">
      <div className="panel__header">
        <h3>Evidence panel</h3>
        <p className="muted">{selectedEvidence.length} linked item(s)</p>
      </div>

      <div className="tab-row">
        {selectedEvidence.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab-row__button${active.id === item.id ? " tab-row__button--active" : ""}`}
            onClick={() => setExpandedId(item.id)}
          >
            {item.id}
          </button>
        ))}
      </div>

      <div className="evidence-card">
        <div className="evidence-card__meta">
          <span>{active.source_type}</span>
          <span>{active.evidence_level}</span>
        </div>
        <h3>{active.path}</h3>
        {active.symbol ? <p className="muted">{active.symbol}</p> : null}
        <p>{active.summary}</p>
      </div>
    </aside>
  );
}
