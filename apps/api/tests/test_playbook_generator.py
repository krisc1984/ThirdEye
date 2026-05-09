import json
from pathlib import Path

from app.schemas.project import Project
from app.services.evidence_builder import EvidenceBuilder
from app.services.playbook_generator import PlaybookGenerator
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def _artifacts(tmp_path):
    scan = ProjectScanner().scan(FIXTURE)
    project = Project(
        id="proj_sample",
        name="Sample Project",
        root_path=FIXTURE,
        slug="sample-project",
        languages=sorted(scan.languages.keys()),
    )
    evidence = EvidenceBuilder().build(project.id, scan)
    generator = PlaybookGenerator(JsonStorage(tmp_path))
    return generator, generator.generate(project, scan, evidence)


def test_generator_creates_required_artifacts(tmp_path):
    generator, artifacts = _artifacts(tmp_path)

    generator.persist(artifacts)
    playbook_dir = tmp_path / "playbooks" / artifacts.metadata.id

    assert (playbook_dir / "playbook.skill.md").exists()
    assert (playbook_dir / "project-summary.md").exists()
    assert (playbook_dir / "rules.json").exists()
    assert (playbook_dir / "evidence.jsonl").exists()
    assert (playbook_dir / "metadata.json").exists()


def test_playbook_contains_required_sections(tmp_path):
    _, artifacts = _artifacts(tmp_path)

    markdown = artifacts.skill_markdown
    assert "## Activation Rules" in markdown
    assert "## Core Maintenance Consensus" in markdown
    assert "## Decision Heuristics" in markdown
    assert "## Anti-Patterns" in markdown
    assert "## Technical Proposal Review Workflow" in markdown
    assert "## Honesty Boundary" in markdown


def test_rules_json_contains_structured_rules(tmp_path):
    generator, artifacts = _artifacts(tmp_path)

    generator.persist(artifacts)
    rules = json.loads((tmp_path / "playbooks" / artifacts.metadata.id / "rules.json").read_text(encoding="utf-8"))

    assert len(rules) >= 5
    assert all("id" in rule for rule in rules)
    assert all("evidence_ids" in rule for rule in rules)

