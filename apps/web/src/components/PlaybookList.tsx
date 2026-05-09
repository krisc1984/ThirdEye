import type { PlaybookMetadata, Project } from "@/lib/api";
import Link from "next/link";

type PlaybookListProps = {
  playbooks: PlaybookMetadata[];
  projects: Project[];
};

export function PlaybookList({ playbooks, projects }: PlaybookListProps) {
  const projectNames = new Map(projects.map((project) => [project.id, project.name]));

  if (!playbooks.length) {
    return (
      <section className="panel">
        <h1>Playbooks</h1>
        <p className="muted">No playbooks have been distilled yet.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="eyebrow">Task 15</p>
          <h1>Playbooks</h1>
        </div>
        <p className="muted">Browse generated review playbooks and inspect their artifacts.</p>
      </div>

      <div className="list-table">
        {playbooks.map((playbook) => (
          <Link key={playbook.id} href={`/playbooks/${playbook.id}`} className="list-table__row">
            <div>
              <strong>{playbook.name}</strong>
              <p>{projectNames.get(playbook.project_id) ?? playbook.project_id}</p>
            </div>
            <div>
              <span>Version</span>
              <strong>{playbook.version}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{playbook.status}</strong>
            </div>
            <div>
              <span>Execution</span>
              <strong>{playbook.execution_mode}</strong>
              <p>{playbook.resolved_provider_id ?? "fallback"}</p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
