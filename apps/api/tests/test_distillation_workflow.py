from pathlib import Path

import pytest

from app.agents.distillation import run_playbook_distillation
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.project import Project
from app.services.evidence_builder import EvidenceBuilder
from app.services.playbook_generator import PlaybookGenerator
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


@pytest.mark.asyncio
async def test_distillation_workflow_enriches_baseline_rules(tmp_path):
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
    provider = ModelProviderConfig(
        id="openai-default",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_shape="responses",
    )

    async def fake_model(_: dict) -> dict:
        rule = {
            "id": "rule_architecture_boundary_001",
            "category": "architecture_boundary",
            "name": "Respect structure with evidence",
            "default_severity": "major",
            "applicability": ["architecture_change"],
            "description": "Architecture changes should stay aligned with observed module boundaries and be treated as inferred when intent is not explicit.",
            "evidence_ids": [evidence[0].id],
            "failure_modes": ["cross-module coupling"],
            "review_prompts": ["Which boundary is changing?"],
        }
        return {
            "rules": [rule],
            "skill_markdown": "# Enriched Skill\n\nClaims without enough proof should be marked as `inferred`.",
        }

    artifacts = await run_playbook_distillation(
        project,
        scan,
        evidence,
        generator,
        provider_config=provider,
        model_runner=fake_model,
    )
    generator.persist(artifacts)

    playbook_dir = tmp_path / "playbooks" / artifacts.metadata.id
    assert any(rule.name == "Respect structure with evidence" for rule in artifacts.rules)
    assert artifacts.rules[0].evidence_ids
    assert "inferred" in artifacts.skill_markdown
    assert (playbook_dir / "playbook.skill.md").exists()
    assert (playbook_dir / "rules.json").exists()
    assert (playbook_dir / "evidence.jsonl").exists()


@pytest.mark.asyncio
async def test_distillation_workflow_falls_back_without_provider(tmp_path):
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

    artifacts = await run_playbook_distillation(project, scan, evidence, generator)

    assert len(artifacts.rules) >= 5
    assert "## Activation Rules" in artifacts.skill_markdown


@pytest.mark.asyncio
async def test_distillation_workflow_uses_provider_runner_when_provider_is_present(tmp_path):
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
    provider = ModelProviderConfig(
        id="openai-default",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_shape="responses",
    )
    calls: list[dict] = []

    async def fake_provider_runner(config: ModelProviderConfig, payload: dict) -> dict:
        calls.append({"provider_id": config.id, "payload": payload})
        return {
            "rules": [
                {
                    "id": "rule_architecture_boundary_001",
                    "category": "architecture_boundary",
                    "name": "Provider-backed rule",
                    "default_severity": "major",
                    "applicability": ["architecture_change"],
                    "description": "Provider call enriched the baseline rule.",
                    "evidence_ids": [evidence[0].id],
                    "failure_modes": [],
                    "review_prompts": [],
                }
            ]
        }

    artifacts = await run_playbook_distillation(
        project,
        scan,
        evidence,
        generator,
        provider_config=provider,
        model_runner=fake_provider_runner,
    )

    assert calls
    assert any(rule.name == "Provider-backed rule" for rule in artifacts.rules)


@pytest.mark.asyncio
async def test_distillation_workflow_maps_provider_native_schema(tmp_path):
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
    provider = ModelProviderConfig(
        id="xunfei",
        name="xunfei",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="astron-code-latest",
        api_shape="chat_completions",
    )

    async def fake_provider_runner(_config: ModelProviderConfig, _payload: dict) -> dict:
        return {
            "status": "needs_information",
            "summary": "The scanned project evidence is incomplete and needs more detail.",
            "findings": [
                {
                    "rule_id": "rule_evidence_gap_001",
                    "category": "honesty_boundary",
                    "severity": "major",
                    "title": "Missing Project Context",
                    "description": "The provider wants more project-specific detail before finalizing stable rules.",
                    "evidence_ids": [evidence[0].id],
                    "suggestion": "Add more architecture and test context.",
                }
            ],
            "compliance_score": 42,
        }

    artifacts = await run_playbook_distillation(
        project,
        scan,
        evidence,
        generator,
        provider_config=provider,
        model_runner=fake_provider_runner,
    )

    assert artifacts.metadata.execution_mode == "llm"
    assert artifacts.metadata.resolved_provider_id == "xunfei"
    assert "Mapped provider-native distillation response" in (artifacts.metadata.execution_note or "")
    assert any(rule.name == "Missing Project Context" for rule in artifacts.rules)
    assert "Provider Summary" in artifacts.skill_markdown


@pytest.mark.asyncio
async def test_distillation_workflow_prefers_agent_distillation_when_provider_is_present(tmp_path, monkeypatch):
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
    provider = ModelProviderConfig(
        id="xunfei",
        name="xunfei",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="astron-code-latest",
        api_shape="chat_completions",
    )
    calls: list[str] = []

    async def fake_agent_distillation(**_kwargs) -> dict:
        calls.append("agent")
        return {
            "rules": [
                {
                    "id": "rule_architecture_boundary_001",
                    "category": "architecture_boundary",
                    "name": "Agent-distilled rule",
                    "default_severity": "major",
                    "applicability": ["architecture_change"],
                    "description": "Generated through the agent distillation path.",
                    "evidence_ids": [evidence[0].id],
                    "failure_modes": [],
                    "review_prompts": [],
                }
            ],
            "skill_markdown": "# Agent Skill\n\nGenerated through agent distillation.",
            "execution_note": "Mapped agent distillation output.",
        }

    monkeypatch.setattr("app.agents.distillation.run_agent_distillation", fake_agent_distillation)

    artifacts = await run_playbook_distillation(
        project,
        scan,
        evidence,
        generator,
        provider_config=provider,
    )

    assert calls == ["agent"]
    assert any(rule.name == "Agent-distilled rule" for rule in artifacts.rules)
    assert "Agent distillation completed" in (artifacts.metadata.execution_note or "")
