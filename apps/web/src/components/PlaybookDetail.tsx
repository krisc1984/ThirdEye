"use client";

import { useState } from "react";

import type { PlaybookDetail as PlaybookDetailType } from "@/lib/api";
import { EvidenceList } from "@/components/EvidenceList";
import { ExecutionDetails } from "@/components/ExecutionDetails";

type PlaybookDetailProps = {
  playbook: PlaybookDetailType;
};

type TabId = "skill" | "rules" | "evidence" | "metadata";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "skill", label: "Skill Markdown" },
  { id: "rules", label: "Rules" },
  { id: "evidence", label: "Evidence" },
  { id: "metadata", label: "Metadata" }
];

export function PlaybookDetail({ playbook }: PlaybookDetailProps) {
  const [activeTab, setActiveTab] = useState<TabId>("skill");

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Playbook Detail</p>
          <h1>{playbook.metadata.name}</h1>
        </div>
        <p className="muted">
          {playbook.metadata.id} · {playbook.metadata.status} · {playbook.metadata.execution_mode} · {playbook.metadata.resolved_provider_id ?? "fallback"}
        </p>
      </div>

      {playbook.metadata.execution_note ? <p className="status status--error">{playbook.metadata.execution_note}</p> : null}

      <ExecutionDetails
        title="Distillation details"
        executionMode={playbook.metadata.execution_mode}
        resolvedProviderId={playbook.metadata.resolved_provider_id}
        executionNote={playbook.metadata.execution_note}
      />

      <div className="tab-row" role="tablist" aria-label="Playbook sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab-row__button${tab.id === activeTab ? " tab-row__button--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "skill" ? (
        <pre className="code-block">{playbook.skill_markdown}</pre>
      ) : null}

      {activeTab === "rules" ? (
        <div className="rule-list">
          {playbook.rules.map((rule) => (
            <article key={rule.id} className="subpanel">
              <div className="rule-list__header">
                <h3>{rule.name}</h3>
                <span>{rule.default_severity}</span>
              </div>
              <p>{rule.description}</p>
              <p className="muted">Applicability: {rule.applicability.join(", ") || "all"}</p>
              <p className="muted">Evidence: {rule.evidence_ids.join(", ") || "none"}</p>
            </article>
          ))}
        </div>
      ) : null}

      {activeTab === "evidence" ? <EvidenceList evidence={playbook.evidence} /> : null}

      {activeTab === "metadata" ? (
        <div className="info-grid">
          <article className="subpanel">
            <h3>Project Summary</h3>
            <pre className="code-block">{playbook.project_summary}</pre>
          </article>
          <article className="subpanel">
            <h3>Metadata</h3>
            <pre className="code-block">{JSON.stringify(playbook.metadata, null, 2)}</pre>
          </article>
        </div>
      ) : null}
    </section>
  );
}
