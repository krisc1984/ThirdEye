"use client";

import { useState } from "react";

import type { EvidenceItem, ReviewResponse } from "@/lib/api";
import { EvidencePanel } from "@/components/EvidencePanel";
import { ExecutionDetails } from "@/components/ExecutionDetails";

type ReviewResultProps = {
  review: ReviewResponse;
  evidence: EvidenceItem[];
};

export function ReviewResult({ review, evidence }: ReviewResultProps) {
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>(
    review.findings.find((finding) => finding.evidence_ids.length)?.evidence_ids ?? []
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Review Output</p>
          <h2>{review.overall_judgement}</h2>
        </div>
        <p className="muted">
          {review.mode} · {review.id} · {review.execution_mode} · {review.resolved_provider_id ?? "fallback"}
        </p>
      </div>

      {review.execution_note ? <p className="status status--error">{review.execution_note}</p> : null}

      <ExecutionDetails
        executionMode={review.execution_mode}
        resolvedProviderId={review.resolved_provider_id}
        executionNote={review.execution_note}
        requestProviderId={review.model_provider}
      />

      <div className="info-grid">
        <article className="subpanel">
          <h3>Key risks</h3>
          <ul className="plain-list">
            {review.key_risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="subpanel">
          <h3>Playbook conflicts</h3>
          <ul className="plain-list">
            {review.playbook_conflicts.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="subpanel">
          <h3>Suggested changes</h3>
          <ul className="plain-list">
            {review.suggested_changes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="subpanel">
          <h3>Required validation</h3>
          <ul className="plain-list">
            {review.required_validation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>

      {review.missing_information.length ? (
        <article className="subpanel">
          <h3>Missing information</h3>
          <ul className="plain-list">
            {review.missing_information.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      ) : null}

      <div className="review-grid">
        <div className="rule-list">
          {review.findings.map((finding, index) => (
            <article key={`${finding.rule_id ?? "finding"}-${index}`} className="subpanel">
              <div className="rule-list__header">
                <h3>{finding.rule_id ?? "General finding"}</h3>
                <span>
                  {finding.severity} · {finding.evidence_level}
                </span>
              </div>
              <p><strong>Problem:</strong> {finding.problem}</p>
              <p><strong>Impact:</strong> {finding.impact}</p>
              <p><strong>Suggested change:</strong> {finding.suggested_change}</p>
              {finding.required_validation.length ? (
                <p className="muted">Validation: {finding.required_validation.join(", ")}</p>
              ) : null}
              {finding.evidence_ids.length ? (
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => setSelectedEvidenceIds(finding.evidence_ids)}
                >
                  Show evidence ({finding.evidence_ids.length})
                </button>
              ) : null}
            </article>
          ))}
        </div>

        <EvidencePanel evidence={evidence} selectedEvidenceIds={selectedEvidenceIds} />
      </div>
    </section>
  );
}
