from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
import logging
from uuid import uuid4

from app.agents.sdk_models import DistillationAgentOutput
from app.agents.sdk_runtime import build_json_prompt, run_structured_agent
from app.model_providers.llm_client import LLMClient
from app.agents.sdk_distillation import run_agent_distillation
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import PlaybookRule
from app.schemas.project import Project, ProjectScanSummary
from app.services.playbook_generator import PlaybookArtifacts, PlaybookGenerator

DistillationModel = Callable[[dict], Awaitable[dict] | dict]
logger = logging.getLogger(__name__)


async def run_playbook_distillation(
    project: Project,
    scan: ProjectScanSummary,
    evidence,
    generator: PlaybookGenerator,
    provider_config: ModelProviderConfig | None = None,
    model_runner: DistillationModel | None = None,
) -> PlaybookArtifacts:
    baseline = generator.generate(project, scan, evidence)
    if provider_config is None and model_runner is None:
        return baseline

    if provider_config is not None:
        baseline.metadata.execution_mode = "llm"
        baseline.metadata.resolved_provider_id = provider_config.id

    if provider_config is not None and model_runner is None:
        payload = {
            "project": project.model_dump(mode="json"),
            "scan": scan.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
            "baseline_skill_markdown": baseline.skill_markdown,
        }
        agent_output = await run_structured_agent(
            name="ThirdEye Distillation Agent",
            instructions=LLMClient().distillation_prompt,
            user_input=build_json_prompt(payload),
            provider_config=provider_config,
            output_type=DistillationAgentOutput,
        )
        result = agent_output.model_dump(mode="json")
    else:
        if model_runner is None and provider_config is not None:
            logger.info(
                "Legacy distillation path selected: %s",
                json.dumps(
                    {
                        "provider_id": provider_config.id,
                        "workflow": "legacy_llm_distillation",
                        "reason": "custom model_runner override not provided, fallback to llm client",
                    },
                    ensure_ascii=False,
                ),
            )
            model_runner = LLMClient().distill_playbook

        prompt_payload = {
            "project": project.model_dump(mode="json"),
            "scan": scan.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "baseline_rules": [rule.model_dump(mode="json") for rule in baseline.rules],
            "baseline_skill_markdown": baseline.skill_markdown,
            "provider": provider_config.model_dump(mode="json") if provider_config is not None else None,
        }
        if provider_config is not None:
            try:
                result = model_runner(provider_config, prompt_payload)
            except TypeError:
                result = model_runner(prompt_payload)
        else:
            result = model_runner(prompt_payload)
    if hasattr(result, "__await__"):
        result = await result  # type: ignore[assignment]
    if not isinstance(result, dict):
        return baseline

    normalized = _normalize_distillation_result(result)
    rules_payload = normalized.get("rules")
    skill_markdown = normalized.get("skill_markdown")
    enriched_rules = _merge_rules(baseline.rules, rules_payload, evidence_ids={item.id for item in evidence})
    if normalized.get("execution_note"):
        baseline.metadata.execution_note = str(normalized["execution_note"])
    if provider_config is not None and baseline.metadata.execution_note:
        baseline.metadata.execution_note = f"Agent distillation completed. {baseline.metadata.execution_note}"
    elif provider_config is not None:
        baseline.metadata.execution_note = "Agent distillation completed with oss-skill style project-skill generation."
    return PlaybookArtifacts(
        metadata=baseline.metadata,
        skill_markdown=skill_markdown if isinstance(skill_markdown, str) and skill_markdown.strip() else baseline.skill_markdown,
        project_summary=baseline.project_summary,
        rules=enriched_rules,
        evidence=baseline.evidence,
    )


def _normalize_distillation_result(result: dict) -> dict:
    native = _normalize_provider_native_distillation(result)
    if native is not None:
        return native
    return result


def _normalize_provider_native_distillation(result: dict) -> dict | None:
    rules_payload = result.get("rules")
    if isinstance(rules_payload, list):
        return None

    findings = result.get("findings")
    summary = result.get("summary")
    if not isinstance(findings, list) or not isinstance(summary, str):
        return None

    mapped_rules: list[dict] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        mapped_rules.append(
            {
                "id": item.get("rule_id") if isinstance(item.get("rule_id"), str) else f"rule_{uuid4().hex[:10]}",
                "category": item.get("category") if isinstance(item.get("category"), str) else "project_specific",
                "name": item.get("title") if isinstance(item.get("title"), str) else "Provider-generated rule",
                "default_severity": item.get("severity") if item.get("severity") in {"blocker", "major", "minor", "nit"} else "major",
                "applicability": ["all"],
                "description": item.get("description") if isinstance(item.get("description"), str) else summary,
                "evidence_ids": [value for value in evidence_ids if isinstance(value, str)],
                "failure_modes": [],
                "review_prompts": [item.get("suggestion")] if isinstance(item.get("suggestion"), str) else [],
                "enabled": True,
            }
        )

    skill_sections = [
        "# Provider-Enriched Review Playbook",
        "",
        "## Provider Summary",
        summary,
    ]
    compliance_score = result.get("compliance_score")
    if compliance_score is not None:
        skill_sections.extend(["", "## Compliance Score", str(compliance_score)])

    return {
        "rules": mapped_rules,
        "skill_markdown": "\n".join(skill_sections),
        "execution_note": "Mapped provider-native distillation response into ThirdEye schema.",
    }


def _merge_rules(
    baseline_rules: list[PlaybookRule],
    rules_payload: object,
    evidence_ids: set[str],
) -> list[PlaybookRule]:
    if not isinstance(rules_payload, list):
        return baseline_rules

    merged_by_id = {rule.id: rule.model_copy(deep=True) for rule in baseline_rules}
    for raw_rule in rules_payload:
        if not isinstance(raw_rule, dict):
            continue
        rule_id = raw_rule.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            continue

        raw_evidence_ids = raw_rule.get("evidence_ids", [])
        if not isinstance(raw_evidence_ids, list):
            raw_evidence_ids = []
        filtered_evidence_ids = [item for item in raw_evidence_ids if isinstance(item, str) and item in evidence_ids]
        if not filtered_evidence_ids and rule_id in merged_by_id:
            filtered_evidence_ids = merged_by_id[rule_id].evidence_ids

        if not filtered_evidence_ids:
            continue

        description = raw_rule.get("description")
        if not isinstance(description, str) or not description.strip():
            continue
        default_severity = raw_rule.get("default_severity")
        if default_severity not in {"blocker", "major", "minor", "nit"}:
            default_severity = "minor"
        applicability = raw_rule.get("applicability")
        if not isinstance(applicability, list):
            applicability = ["all"]
        failure_modes = raw_rule.get("failure_modes")
        if not isinstance(failure_modes, list):
            failure_modes = []
        review_prompts = raw_rule.get("review_prompts")
        if not isinstance(review_prompts, list):
            review_prompts = []

        merged_by_id[rule_id] = PlaybookRule(
            id=rule_id,
            category=str(raw_rule.get("category") or "project_specific"),
            name=str(raw_rule.get("name") or rule_id),
            default_severity=default_severity,
            applicability=[str(item) for item in applicability if str(item).strip()],
            description=description.strip(),
            evidence_ids=filtered_evidence_ids,
            failure_modes=[str(item) for item in failure_modes if str(item).strip()],
            review_prompts=[str(item) for item in review_prompts if str(item).strip()],
            enabled=bool(raw_rule.get("enabled", True)),
        )

    ordered_ids = [rule.id for rule in baseline_rules]
    extras = [rule_id for rule_id in merged_by_id if rule_id not in ordered_ids]
    return [merged_by_id[rule_id] for rule_id in [*ordered_ids, *extras]]
