from __future__ import annotations

import json
from pathlib import Path

from app.schemas.project import Project
from app.services.evidence_builder import EvidenceBuilder
from app.services.playbook_generator import PlaybookGenerator
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[3]
    fixture_root = workspace_root / "apps" / "api" / "tests" / "fixtures" / "sample_project"
    data_root = workspace_root / "data"

    scanner = ProjectScanner()
    scan = scanner.scan(fixture_root)
    project = Project(
        id="proj_sample_fixture",
        name="Sample Project",
        root_path=fixture_root,
        slug="sample-project",
        languages=sorted(scan.languages.keys()),
    )

    storage = JsonStorage(data_root)
    storage.save_json(
        "projects",
        project.id,
        {
          **project.model_dump(mode="json"),
          "latest_scan": scan.model_dump(mode="json"),
        },
    )

    evidence = EvidenceBuilder().build(project.id, scan)
    generator = PlaybookGenerator(storage)
    artifacts = generator.generate(project, scan, evidence)
    generator.persist(artifacts)

    output = {
        "project_id": project.id,
        "playbook_id": artifacts.metadata.id,
        "root_path": str(fixture_root),
        "playbook_path": str((data_root / "playbooks" / artifacts.metadata.id).resolve()),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
