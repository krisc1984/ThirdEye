"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { PlaybookMetadata } from "@/lib/api";
import { distillPlaybook } from "@/lib/api";
import { ExecutionDetails } from "@/components/ExecutionDetails";

type DistillProjectButtonProps = {
  projectId: string;
  modelProviderId?: string;
};

export function DistillProjectButton({ projectId, modelProviderId }: DistillProjectButtonProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlaybookMetadata | null>(null);
  const [isPending, startTransition] = useTransition();

  return (
    <div className="action-stack">
      <button
        type="button"
        className="button button--primary"
        disabled={isPending}
        onClick={() => {
          setError(null);
          setResult(null);
          startTransition(async () => {
            try {
              const playbook = await distillPlaybook({
                project_id: projectId,
                ...(modelProviderId ? { model_provider_id: modelProviderId } : {})
              });
              setResult(playbook);
              router.push(`/playbooks/${playbook.id}`);
            } catch (caughtError) {
              setError(caughtError instanceof Error ? caughtError.message : "Failed to distill playbook.");
            }
          });
        }}
      >
        {isPending ? "Distilling..." : modelProviderId ? "Start LLM Distillation" : "Start Distillation"}
      </button>
      <p className="muted">
        {modelProviderId
          ? `Using provider: ${modelProviderId}`
          : "Using deterministic fallback because no model provider is selected."}
      </p>
      <p className="muted">
        {modelProviderId
          ? "If the provider call fails, the backend will fall back and record the reason in execution details."
          : "Select a provider above if you want this step to call a real LLM API."}
      </p>
      {error ? <p className="status status--error">{error}</p> : null}
      {result ? (
        <>
          <p className={`status ${result.execution_mode === "llm" ? "status--success" : "status--warning"}`}>
            Created playbook <strong>{result.name}</strong> with <code>{result.execution_mode}</code> execution.
          </p>
          <ExecutionDetails
            title="Latest distillation run"
            executionMode={result.execution_mode}
            resolvedProviderId={result.resolved_provider_id}
            executionNote={result.execution_note}
            requestProviderId={modelProviderId || null}
          />
        </>
      ) : null}
    </div>
  );
}
