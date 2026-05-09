from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
import logging
from uuid import uuid4

from app.agents.sdk_models import ReviewAgentOutput
from app.agents.sdk_runtime import build_json_prompt, run_structured_agent
from app.model_providers.llm_client import LLMClient
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from app.schemas.review import ReviewFinding, ReviewRequest, ReviewResponse

ReviewModel = Callable[[dict], Awaitable[dict] | dict]
logger = logging.getLogger(__name__)


async def run_review(
    request: ReviewRequest,
    metadata: PlaybookMetadata,
    rules: list[PlaybookRule],
    evidence: list[EvidenceItem],
    provider_config: ModelProviderConfig | None = None,
    model_runner: ReviewModel | None = None,
) -> ReviewResponse:
    if provider_config is not None or model_runner is not None:
        payload = {
            "request": request.model_dump(mode="json"),
            "playbook": metadata.model_dump(mode="json"),
            "rules": [rule.model_dump(mode="json") for rule in rules],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "provider": provider_config.model_dump(mode="json") if provider_config is not None else None,
        }
        if model_runner is None and provider_config is not None:
            agent_output = await run_structured_agent(
                name="ThirdEye Review Agent",
                instructions=LLMClient().review_prompt,
                user_input=build_json_prompt(payload),
                provider_config=provider_config,
                output_type=ReviewAgentOutput,
            )
            result = agent_output.model_dump(mode="json")
        else:
            if provider_config is not None:
                try:
                    result = model_runner(provider_config, payload)
                except TypeError:
                    result = model_runner(payload)
            else:
                result = model_runner(payload)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        if isinstance(result, dict):
            custom = _response_from_model(result, request)
            if custom is not None:
                return custom
            logger.warning(
                "LLM review response schema invalid; falling back to deterministic. provider=%s response=%s",
                request.model_provider_id,
                json.dumps(result, ensure_ascii=False)[:1200],
            )

    return _deterministic_review(request, metadata, rules, evidence)


def _response_from_model(result: dict, request: ReviewRequest) -> ReviewResponse | None:
    native = _response_from_provider_native_schema(result, request)
    if native is not None:
        return native

    try:
        findings = [ReviewFinding.model_validate(item) for item in result.get("findings", [])]
        return ReviewResponse(
            id=result.get("id") or f"rev_{uuid4().hex[:12]}",
            playbook_id=request.playbook_id,
            mode=request.mode,
            input=request.proposal,
            execution_mode="llm",
            resolved_provider_id=request.model_provider_id,
            overall_judgement=result["overall_judgement"],
            key_risks=list(result.get("key_risks", [])),
            playbook_conflicts=list(result.get("playbook_conflicts", [])),
            suggested_changes=list(result.get("suggested_changes", [])),
            required_validation=list(result.get("required_validation", [])),
            missing_information=list(result.get("missing_information", [])),
            findings=findings,
            model_provider=request.model_provider_id,
        )
    except Exception:
        return None


def _response_from_provider_native_schema(result: dict, request: ReviewRequest) -> ReviewResponse | None:
    status = result.get("status")
    summary = result.get("summary")
    findings_payload = result.get("findings")
    if not isinstance(status, str) or not isinstance(summary, str) or not isinstance(findings_payload, list):
        return None

    findings: list[ReviewFinding] = []
    key_risks: list[str] = []
    conflicts: list[str] = []
    suggested_changes: list[str] = []
    required_validation: list[str] = []
    missing_information: list[str] = []

    for item in findings_payload:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity")
        if severity not in {"blocker", "major", "minor", "nit"}:
            severity = "major"

        title = item.get("title")
        description = item.get("description")
        suggestion = item.get("suggestion")
        evidence_ids = item.get("evidence_ids")

        if not isinstance(title, str) or not isinstance(description, str):
            continue
        if not isinstance(suggestion, str):
            suggestion = "Please provide more project-specific implementation detail."
        if not isinstance(evidence_ids, list):
            evidence_ids = []

        status_lower = status.lower()
        evidence_level = "inferred"
        if "compliant" in status_lower or "pass" in status_lower:
            evidence_level = "confirmed"
        elif "needs_information" in status_lower:
            evidence_level = "unknown"

        finding = ReviewFinding(
            severity=severity,
            confidence=0.78,
            evidence_level=evidence_level,  # type: ignore[arg-type]
            rule_id=item.get("rule_id") if isinstance(item.get("rule_id"), str) else None,
            problem=title,
            impact=description,
            suggested_change=suggestion,
            required_validation=[],
            evidence_ids=[value for value in evidence_ids if isinstance(value, str)],
        )
        findings.append(finding)
        key_risks.append(title)
        conflicts.append(description)
        suggested_changes.append(suggestion)

    overall_judgement = _map_provider_status_to_judgement(status)
    if status.lower() == "needs_information":
        missing_information.append(summary)

    if not findings and summary:
        key_risks.append(summary)

    return ReviewResponse(
        id=result.get("review_id") if isinstance(result.get("review_id"), str) else f"rev_{uuid4().hex[:12]}",
        playbook_id=request.playbook_id,
        mode=request.mode,
        input=request.proposal,
        execution_mode="llm",
        resolved_provider_id=request.model_provider_id,
        execution_note="Mapped provider-native review response into ThirdEye schema.",
        overall_judgement=overall_judgement,
        key_risks=list(dict.fromkeys(key_risks)),
        playbook_conflicts=list(dict.fromkeys(conflicts)),
        suggested_changes=list(dict.fromkeys(suggested_changes)),
        required_validation=list(dict.fromkeys(required_validation)),
        missing_information=list(dict.fromkeys(missing_information)),
        findings=findings,
        model_provider=request.model_provider_id,
    )


def _map_provider_status_to_judgement(status: str) -> str:
    normalized = status.strip().lower()
    mapping = {
        "approved": "通过",
        "pass": "通过",
        "conditional_pass": "有条件通过",
        "needs_information": "有条件通过",
        "revise": "建议修改后再评审",
        "needs_revision": "建议修改后再评审",
        "reject": "不建议采用",
        "fail": "不建议采用",
    }
    return mapping.get(normalized, "有条件通过")


def _deterministic_review(
    request: ReviewRequest,
    metadata: PlaybookMetadata,
    rules: list[PlaybookRule],
    evidence: list[EvidenceItem],
) -> ReviewResponse:
    proposal = request.proposal.strip()
    proposal_lower = proposal.lower()
    findings: list[ReviewFinding] = []
    key_risks: list[str] = []
    conflicts: list[str] = []
    suggested_changes: list[str] = []
    required_validation: list[str] = []
    missing_information: list[str] = []

    for rule in rules:
        finding = _evaluate_rule(rule, proposal_lower)
        if finding is None:
            continue
        findings.append(finding)
        key_risks.append(finding.problem)
        conflicts.append(f"{rule.name}: {finding.impact}")
        suggested_changes.append(finding.suggested_change)
        required_validation.extend(finding.required_validation)

    if len(proposal) < 40:
        missing_information.append("方案描述过短，缺少模块边界、验证计划和受影响范围。")
    if "test" not in proposal_lower and "验证" not in proposal:
        missing_information.append("没有说明如何沿用现有测试或验证路径。")
    if "module" not in proposal_lower and "模块" not in proposal and "service" not in proposal_lower:
        missing_information.append("没有明确说明变更会触达哪些模块边界。")

    judgement = "通过"
    if findings:
        severities = {item.severity for item in findings}
        if "blocker" in severities:
            judgement = "不建议采用"
        elif "major" in severities:
            judgement = "建议修改后再评审"
        else:
            judgement = "有条件通过"
    elif missing_information:
        judgement = "有条件通过"

    dedup_required_validation = list(dict.fromkeys(required_validation))
    dedup_changes = list(dict.fromkeys(suggested_changes))
    dedup_risks = list(dict.fromkeys(key_risks))
    dedup_conflicts = list(dict.fromkeys(conflicts))
    dedup_missing = list(dict.fromkeys(missing_information))

    if not findings:
        dedup_risks.append(f"当前未发现与 {metadata.name} 直接冲突的高风险规则，但仍需补齐项目化验证。")
        dedup_changes.append("补充涉及模块、验证方式和回滚路径后再推进实施。")
        dedup_required_validation.append("至少补充一条与现有项目测试风格一致的验证步骤。")

    return ReviewResponse(
        id=f"rev_{uuid4().hex[:12]}",
        playbook_id=request.playbook_id,
        mode=request.mode,
        input=request.proposal,
        execution_mode="deterministic",
        resolved_provider_id=None,
        overall_judgement=judgement,
        key_risks=dedup_risks,
        playbook_conflicts=dedup_conflicts,
        suggested_changes=dedup_changes,
        required_validation=dedup_required_validation,
        missing_information=dedup_missing,
        findings=findings,
        model_provider=request.model_provider_id,
    )


def _evaluate_rule(rule: PlaybookRule, proposal_lower: str) -> ReviewFinding | None:
    category = rule.category.lower()
    if category == "architecture_boundary" and not _contains_any(proposal_lower, ["module", "boundary", "service", "模块", "边界"]):
        return ReviewFinding(
            severity=rule.default_severity,
            confidence=0.83,
            evidence_level="inferred",
            rule_id=rule.id,
            problem="方案没有说明如何保持现有模块边界。",
            impact="缺少边界说明会让新增层次或跨模块耦合难以评估。",
            suggested_change="补充受影响模块、依赖方向和迁移路径。",
            required_validation=["确认变更后的模块依赖关系与当前结构一致。"],
            evidence_ids=rule.evidence_ids,
        )
    if category == "testing" and not _contains_any(proposal_lower, ["test", "pytest", "验证", "测试"]):
        return ReviewFinding(
            severity=rule.default_severity,
            confidence=0.9,
            evidence_level="confirmed",
            rule_id=rule.id,
            problem="方案缺少与项目现有测试风格一致的验证计划。",
            impact="没有回归验证会放大重构或新功能引入后的行为风险。",
            suggested_change="明确需要补充的自动化测试或最小可行验证步骤。",
            required_validation=["补充至少一个现有测试风格下的回归验证。"],
            evidence_ids=rule.evidence_ids,
        )
    if category == "documentation" and not _contains_any(proposal_lower, ["readme", "doc", "文档", "说明"]):
        return ReviewFinding(
            severity="minor",
            confidence=0.62,
            evidence_level="inferred",
            rule_id=rule.id,
            problem="方案没有说明是否会影响现有文档约束或操作说明。",
            impact="如果行为变化未同步到项目文档，后续维护会出现偏差。",
            suggested_change="标注需要更新的 README、设计说明或运行文档。",
            required_validation=["检查是否存在需要同步更新的项目文档。"],
            evidence_ids=rule.evidence_ids,
        )
    return None


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)
