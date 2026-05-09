import json
from pathlib import Path

import pytest

from app.agents.review import run_review
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from app.schemas.review import ReviewRequest
from app.services.playbook_loader import PlaybookLoader
from app.services.storage import JsonStorage


def _write_sample_playbook(storage: JsonStorage) -> str:
    playbook_id = "pb_sample_v1"
    metadata = PlaybookMetadata(
        id=playbook_id,
        project_id="proj_sample",
        name="Sample Review Playbook",
        version="1.0.0",
        status="active",
        skill_path=Path("data/playbooks/pb_sample_v1/playbook.skill.md"),
        rules_path=Path("data/playbooks/pb_sample_v1/rules.json"),
        evidence_path=Path("data/playbooks/pb_sample_v1/evidence.jsonl"),
    )
    rules = [
        PlaybookRule(
            id="rule_architecture_boundary_001",
            category="architecture_boundary",
            name="Respect module boundaries",
            default_severity="major",
            applicability=["new_feature"],
            description="Describe impacted modules before changing structure.",
            evidence_ids=["ev_arch"],
            review_prompts=["What modules change?"],
        ),
        PlaybookRule(
            id="rule_test_strategy_001",
            category="testing",
            name="Keep project-style validation",
            default_severity="major",
            applicability=["new_feature"],
            description="Include concrete regression validation.",
            evidence_ids=["ev_test"],
            review_prompts=["How is it tested?"],
        ),
    ]
    evidence = [
        EvidenceItem(
            id="ev_arch",
            project_id="proj_sample",
            source_type="code",
            path="src/app.py",
            summary="Primary application module defines the current structure.",
            evidence_level="confirmed",
        ),
        EvidenceItem(
            id="ev_test",
            project_id="proj_sample",
            source_type="test",
            path="tests/test_app.py",
            summary="Project already uses automated pytest coverage.",
            evidence_level="confirmed",
        ),
    ]
    storage.save_playbook_artifact(playbook_id, "metadata.json", json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False))
    storage.save_playbook_artifact(playbook_id, "playbook.skill.md", "# Sample")
    storage.save_playbook_artifact(playbook_id, "project-summary.md", "# Summary")
    storage.save_playbook_artifact(
        playbook_id,
        "rules.json",
        json.dumps([rule.model_dump(mode="json") for rule in rules], ensure_ascii=False),
    )
    storage.save_playbook_artifact(
        playbook_id,
        "evidence.jsonl",
        "\n".join(json.dumps(item.model_dump(mode="json"), ensure_ascii=False) for item in evidence),
    )
    return playbook_id


def test_playbook_loader_reads_all_artifacts(tmp_path):
    storage = JsonStorage(tmp_path)
    playbook_id = _write_sample_playbook(storage)

    loaded = PlaybookLoader(storage).load(playbook_id)

    assert loaded.metadata.id == playbook_id
    assert loaded.skill_markdown == "# Sample"
    assert len(loaded.rules) == 2
    assert len(loaded.evidence) == 2


@pytest.mark.asyncio
async def test_review_workflow_returns_structured_response(tmp_path):
    storage = JsonStorage(tmp_path)
    playbook_id = _write_sample_playbook(storage)
    loaded = PlaybookLoader(storage).load(playbook_id)
    request = ReviewRequest(
        playbook_id=playbook_id,
        proposal="Add a new async task runner to the system.",
        mode="strict",
    )

    response = await run_review(request, loaded.metadata, loaded.rules, loaded.evidence)

    assert response.overall_judgement in {"通过", "有条件通过", "建议修改后再评审", "不建议采用"}
    assert response.key_risks
    assert response.playbook_conflicts
    assert response.suggested_changes
    assert response.required_validation
    assert any(finding.evidence_level in {"confirmed", "inferred"} for finding in response.findings)


@pytest.mark.asyncio
async def test_review_workflow_uses_provider_runner_when_provider_is_present(tmp_path):
    storage = JsonStorage(tmp_path)
    playbook_id = _write_sample_playbook(storage)
    loaded = PlaybookLoader(storage).load(playbook_id)
    provider = ModelProviderConfig(
        id="router-api",
        name="Router",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="provider/model",
        api_shape="chat_completions",
    )
    request = ReviewRequest(
        playbook_id=playbook_id,
        proposal="Add a background worker and keep the change within one module with pytest coverage.",
        mode="standard",
        model_provider_id=provider.id,
    )
    calls: list[dict] = []

    async def fake_provider_runner(config: ModelProviderConfig, payload: dict) -> dict:
        calls.append({"provider_id": config.id, "payload": payload})
        return {
            "overall_judgement": "有条件通过",
            "key_risks": ["Provider-backed risk"],
            "playbook_conflicts": ["Conflict from model"],
            "suggested_changes": ["Add more rollout detail"],
            "required_validation": ["Run pytest"],
            "missing_information": [],
            "findings": [
                {
                    "severity": "major",
                    "confidence": 0.8,
                    "evidence_level": "confirmed",
                    "rule_id": "rule_test_strategy_001",
                    "problem": "Need stronger validation detail.",
                    "impact": "Release confidence is lower without it.",
                    "suggested_change": "Document the test plan.",
                    "required_validation": ["Run pytest"],
                    "evidence_ids": ["ev_test"],
                }
            ],
        }

    response = await run_review(
        request,
        loaded.metadata,
        loaded.rules,
        loaded.evidence,
        provider_config=provider,
        model_runner=fake_provider_runner,
    )

    assert calls
    assert response.overall_judgement == "有条件通过"
    assert response.findings[0].rule_id == "rule_test_strategy_001"


@pytest.mark.asyncio
async def test_review_workflow_maps_provider_native_schema(tmp_path):
    storage = JsonStorage(tmp_path)
    playbook_id = _write_sample_playbook(storage)
    loaded = PlaybookLoader(storage).load(playbook_id)
    provider = ModelProviderConfig(
        id="xunfei",
        name="xunfei",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="astron-code-latest",
        api_shape="chat_completions",
    )
    request = ReviewRequest(
        playbook_id=playbook_id,
        proposal="测试",
        mode="standard",
        model_provider_id=provider.id,
    )

    async def fake_provider_runner(_config: ModelProviderConfig, _payload: dict) -> dict:
        return {
            "review_id": "rev_native_001",
            "playbook_id": playbook_id,
            "status": "needs_information",
            "summary": "The proposal content is insufficient for evaluation.",
            "findings": [
                {
                    "rule_id": "rule_evidence_gap_001",
                    "category": "honesty_boundary",
                    "severity": "major",
                    "title": "Missing Proposal Content",
                    "description": "There is no technical detail to evaluate.",
                    "evidence_ids": ["ev_arch"],
                    "location": None,
                    "suggestion": "Provide a complete technical proposal.",
                }
            ],
            "compliance_score": 0,
            "generated_at": "2026-05-07T09:15:00.000000Z",
        }

    response = await run_review(
        request,
        loaded.metadata,
        loaded.rules,
        loaded.evidence,
        provider_config=provider,
        model_runner=fake_provider_runner,
    )

    assert response.execution_mode == "llm"
    assert response.resolved_provider_id == "xunfei"
    assert response.overall_judgement == "有条件通过"
    assert response.findings[0].problem == "Missing Proposal Content"
    assert "Mapped provider-native review response" in (response.execution_note or "")
