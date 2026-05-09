"use client";

import { useState, useTransition } from "react";

import type { ModelProviderConfig, Project, ProjectScanSummary } from "@/lib/api";
import { createProject, scanProject } from "@/lib/api";
import { DistillProjectButton } from "@/components/DistillProjectButton";
import { ProjectScanSummary as ProjectScanSummaryView } from "@/components/ProjectScanSummary";

type ProjectScanFormProps = {
  modelProviders: ModelProviderConfig[];
  projects: Project[];
};

export function ProjectScanForm({ modelProviders, projects }: ProjectScanFormProps) {
  const [rootPath, setRootPath] = useState("");
  const [projectName, setProjectName] = useState("");
  const [extraIgnorePatterns, setExtraIgnorePatterns] = useState("");
  const [modelProviderId, setModelProviderId] = useState(modelProviders[0]?.id ?? "");
  const [selectedProjectId, setSelectedProjectId] = useState(projects[0]?.id ?? "");
  const [summary, setSummary] = useState<ProjectScanSummary | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const patterns = extraIgnorePatterns
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="eyebrow">Saved Projects</p>
            <h1>Distill From Existing Project</h1>
          </div>
          <p className="muted">Reuse a saved project directly when you only want to re-run distillation.</p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>Saved project</span>
            <select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
              <option value="">Select saved project</option>
              {projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Distillation provider</span>
            <select value={modelProviderId} onChange={(event) => setModelProviderId(event.target.value)}>
              <option value="">Deterministic fallback</option>
              {modelProviders.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
          </label>

          {selectedProjectId ? (
            <div className="field field--full">
              <DistillProjectButton projectId={selectedProjectId} modelProviderId={modelProviderId || undefined} />
            </div>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="eyebrow">New Project</p>
            <h1>Scan And Save Project</h1>
          </div>
          <p className="muted">Scan a local path, save it once, then reuse it later from the saved project list above.</p>
        </div>

        <form className="form-grid">
          <label className="field">
            <span>Project root path</span>
            <input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="F:\\repo\\your-project" />
          </label>

          <label className="field">
            <span>Project name</span>
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Optional display name" />
          </label>

          <label className="field">
            <span>Distillation provider for later run</span>
            <input value={modelProviderId || "deterministic"} readOnly />
          </label>

          <div className="subpanel field--full">
            <h3>Execution preview</h3>
            <p className="muted">
              {modelProviderId
                ? `This distillation will try provider "${modelProviderId}" first, then fall back to deterministic generation if the API call fails.`
                : "No model provider selected. This run will stay deterministic and will not call any LLM API."}
            </p>
          </div>

          <label className="field field--full">
            <span>Extra ignore patterns</span>
            <textarea
              rows={5}
              value={extraIgnorePatterns}
              onChange={(event) => setExtraIgnorePatterns(event.target.value)}
              placeholder=".cache&#10;coverage&#10;tmp"
            />
          </label>

          <div className="action-row field--full">
            <button
              type="button"
              className="button"
              disabled={isPending || !rootPath.trim()}
              onClick={() => {
                setError(null);
                startTransition(async () => {
                  try {
                    const nextSummary = await scanProject({
                      root_path: rootPath.trim(),
                      extra_ignore_patterns: patterns
                    });
                    setSummary(nextSummary);
                  } catch (caughtError) {
                    setError(caughtError instanceof Error ? caughtError.message : "Scan failed.");
                  }
                });
              }}
            >
              {isPending ? "Working..." : "Scan"}
            </button>

            <button
              type="button"
              className="button button--secondary"
              disabled={isPending || !rootPath.trim()}
              onClick={() => {
                setError(null);
                startTransition(async () => {
                  try {
                    const nextProject = await createProject({
                      root_path: rootPath.trim(),
                      extra_ignore_patterns: patterns,
                      ...(projectName.trim() ? { name: projectName.trim() } : {})
                    });
                    setProject(nextProject);
                  } catch (caughtError) {
                    setError(caughtError instanceof Error ? caughtError.message : "Project creation failed.");
                  }
                });
              }}
            >
              Save Project
            </button>

            {project ? <DistillProjectButton projectId={project.id} modelProviderId={modelProviderId || undefined} /> : null}
          </div>
        </form>

        {project ? (
          <p className="status status--success">
            Saved project <strong>{project.name}</strong> as <code>{project.id}</code>. You can now select it from the saved project section above.
          </p>
        ) : null}
        {error ? <p className="status status--error">{error}</p> : null}
      </section>

      {summary ? <ProjectScanSummaryView summary={summary} /> : null}
    </div>
  );
}
