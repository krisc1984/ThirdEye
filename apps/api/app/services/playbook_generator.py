from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from app.schemas.project import Project, ProjectScanSummary
from app.services.storage import JsonStorage


@dataclass(frozen=True)
class PlaybookArtifacts:
    metadata: PlaybookMetadata
    skill_markdown: str
    project_summary: str
    rules: list[PlaybookRule]
    evidence: list[EvidenceItem]


class PlaybookGenerator:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def generate(
        self,
        project: Project,
        scan: ProjectScanSummary,
        evidence: list[EvidenceItem],
    ) -> PlaybookArtifacts:
        playbook_id = f"pb_{project.slug}_v1"
        rules = self._build_rules(evidence)
        skill_markdown = self._render_skill(project, scan, rules, evidence)
        project_summary = self._render_project_summary(project, scan, evidence)
        playbook_dir = Path("data") / "playbooks" / playbook_id
        metadata = PlaybookMetadata(
            id=playbook_id,
            project_id=project.id,
            name=f"{project.name} Review Playbook",
            version="1.0.0",
            status="active",
            orchestration_mode="project_skill_agent",
            skill_path=playbook_dir / "playbook.skill.md",
            agent_skill_path=playbook_dir / "project-reviewer.skill.md",
            rules_path=playbook_dir / "rules.json",
            evidence_path=playbook_dir / "evidence.jsonl",
            created_at=datetime.utcnow(),
        )
        return PlaybookArtifacts(
            metadata=metadata,
            skill_markdown=skill_markdown,
            project_summary=project_summary,
            rules=rules,
            evidence=evidence,
        )

    def persist(self, artifacts: PlaybookArtifacts) -> None:
        playbook_id = artifacts.metadata.id
        self.storage.save_playbook_artifact(
            playbook_id,
            "metadata.json",
            json.dumps(artifacts.metadata.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )
        self.storage.save_playbook_artifact(
            playbook_id,
            "playbook.skill.md",
            artifacts.skill_markdown,
        )
        self.storage.save_playbook_artifact(
            playbook_id,
            "project-reviewer.skill.md",
            artifacts.skill_markdown,
        )
        self.storage.save_playbook_artifact(
            playbook_id,
            "project-summary.md",
            artifacts.project_summary,
        )
        self.storage.save_playbook_artifact(
            playbook_id,
            "rules.json",
            json.dumps(
                [rule.model_dump(mode="json") for rule in artifacts.rules],
                ensure_ascii=False,
                indent=2,
            ),
        )
        self.storage.save_playbook_artifact(
            playbook_id,
            "evidence.jsonl",
            "\n".join(
                json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
                for item in artifacts.evidence
            ),
        )

    def enrich(
        self,
        artifacts: PlaybookArtifacts,
        *,
        rules: list[PlaybookRule] | None = None,
        skill_markdown: str | None = None,
    ) -> PlaybookArtifacts:
        return PlaybookArtifacts(
            metadata=artifacts.metadata,
            skill_markdown=skill_markdown if skill_markdown is not None else artifacts.skill_markdown,
            project_summary=artifacts.project_summary,
            rules=rules if rules is not None else artifacts.rules,
            evidence=artifacts.evidence,
        )

    def _build_rules(self, evidence: list[EvidenceItem]) -> list[PlaybookRule]:
        by_type: dict[str, list[str]] = {}
        for item in evidence:
            by_type.setdefault(item.source_type, []).append(item.id)

        return [
            PlaybookRule(
                id="rule_architecture_boundary_001",
                category="architecture_boundary",
                name="Respect existing project structure and module boundaries",
                default_severity="major",
                applicability=["architecture_change", "new_feature", "refactor"],
                description="New technical proposals should fit the discovered project structure before adding new layers or cross-cutting paths.",
                evidence_ids=self._first_ids(by_type, ["code", "doc"], 3),
                failure_modes=["unexplained new layer", "cross-module coupling", "unclear ownership"],
                review_prompts=["Does the proposal preserve the existing module boundary model?"],
            ),
            PlaybookRule(
                id="rule_documented_constraints_001",
                category="documentation",
                name="Honor documented project constraints",
                default_severity="major",
                applicability=["architecture_change", "api_design", "new_feature"],
                description="When project documents state constraints or workflow expectations, proposals should address them explicitly.",
                evidence_ids=self._first_ids(by_type, ["doc"], 3),
                failure_modes=["ignores README guidance", "undocumented behavior change"],
                review_prompts=["Which documented constraints does this proposal depend on or change?"],
            ),
            PlaybookRule(
                id="rule_test_strategy_001",
                category="testing",
                name="Include validation aligned with existing tests",
                default_severity="major",
                applicability=["new_feature", "refactor", "performance", "api_design"],
                description="Technical proposals should identify tests or verification steps matching the project's existing testing style.",
                evidence_ids=self._first_ids(by_type, ["test"], 3),
                failure_modes=["no regression plan", "tests do not match existing coverage style"],
                review_prompts=["What existing test style should validate this change?"],
            ),
            PlaybookRule(
                id="rule_tooling_constraints_001",
                category="tooling",
                name="Account for project tooling and runtime configuration",
                default_severity="minor",
                applicability=["dependency_change", "build_change", "ops_change"],
                description="Build, lint, runtime, and packaging configuration should be treated as project constraints.",
                evidence_ids=self._first_ids(by_type, ["config"], 3),
                failure_modes=["tooling drift", "unvalidated runtime config"],
                review_prompts=["Does the proposal update or depend on existing project tooling?"],
            ),
            PlaybookRule(
                id="rule_evidence_gap_001",
                category="honesty_boundary",
                name="Call out missing project evidence instead of assuming intent",
                default_severity="minor",
                applicability=["all"],
                description="If the playbook lacks evidence for a conclusion, the review must ask for missing information instead of inventing project standards.",
                evidence_ids=self._first_ids(by_type, ["doc", "code", "test", "config"], 5),
                failure_modes=["generic advice", "unsupported maintainer claim"],
                review_prompts=["Is this conclusion backed by project evidence or only inferred?"],
            ),
        ]

    def _first_ids(self, by_type: dict[str, list[str]], source_types: list[str], limit: int) -> list[str]:
        ids: list[str] = []
        for source_type in source_types:
            ids.extend(by_type.get(source_type, []))
        return ids[:limit]

    def _render_skill(
        self,
        project: Project,
        scan: ProjectScanSummary,
        rules: list[PlaybookRule],
        evidence: list[EvidenceItem],
    ) -> str:
        consensus = [
            "Use project-local evidence before making architectural claims.",
            "Preserve discovered module boundaries unless the proposal explains a migration path.",
            "Match validation plans to existing tests and tooling.",
        ]
        anti_patterns = [
            "Adding broad abstractions without evidence of repeated project needs.",
            "Changing architecture without naming affected modules and validation paths.",
            "Presenting generic best practices as project-specific requirements.",
        ]
        rules_md = "\n".join(
            f"- **{rule.id}**: {rule.name} ({rule.default_severity})\n  - {rule.description}"
            for rule in rules
        )
        evidence_md = "\n".join(
            f"- `{item.id}` `{item.source_type}` `{item.path}`: {item.summary}"
            for item in evidence[:20]
        )
        return f"""---
name: {project.slug}-review-playbook
description: |
  Review technical proposals against the discovered engineering constraints of {project.name}.
  Use this skill when a user selects the {project.name} project playbook and asks for technical plan review.
---

# {project.name} Review Playbook

## Activation Rules

- Use this playbook only for technical proposal review for `{project.root_path}`.
- Do not perform code review, diff review, PR review, or source code modification.
- Prefer project evidence over generic engineering advice.
- Mark unsupported claims as `inferred` or `unknown`.

## Project Summary

- Languages: {", ".join(project.languages) or "unknown"}
- Scanned files: {scan.scanned_files}
- Documents: {len(scan.docs)}
- Tests: {len(scan.tests)}
- Config files: {len(scan.config_files)}

## Core Maintenance Consensus

{chr(10).join(f"- {item}" for item in consensus)}

## Decision Heuristics

{rules_md}

## Anti-Patterns

{chr(10).join(f"- {item}" for item in anti_patterns)}

## Technical Proposal Review Workflow

1. Classify the proposal: new feature, refactor, API design, dependency change, performance change, or operations change.
2. Retrieve the rules that apply to that proposal type.
3. Compare the proposal with project evidence and note conflicts.
4. Return an overall judgement: `通过`, `有条件通过`, `建议修改后再评审`, or `不建议采用`.
5. Include required validation and missing information.

## Evidence Levels

- `confirmed`: directly supported by project files.
- `inferred`: likely from project structure, but not explicitly documented.
- `preference`: lower-confidence project tendency.
- `unknown`: evidence is not available.

## Honesty Boundary

This playbook is generated from local files only. It does not include GitHub issues, PR reviews, or external maintainer discussion.

## Evidence Preview

{evidence_md}
"""

    def _render_project_summary(
        self,
        project: Project,
        scan: ProjectScanSummary,
        evidence: list[EvidenceItem],
    ) -> str:
        return f"""# {project.name} Project Summary

- Root path: `{project.root_path}`
- Languages: {", ".join(project.languages) or "unknown"}
- Scanned files: {scan.scanned_files}
- Skipped files: {scan.skipped_files}
- Documents: {", ".join(scan.docs) or "none"}
- Tests: {", ".join(scan.tests) or "none"}
- Config files: {", ".join(scan.config_files) or "none"}
- Evidence count: {len(evidence)}
"""
