from pathlib import Path
import asyncio

from app.agents import sdk_distillation
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.project import Project
from app.services.evidence_builder import EvidenceBuilder
from app.services.playbook_generator import PlaybookGenerator
from app.services.project_scanner import ProjectScanner
from app.services.storage import JsonStorage


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_run_agent_distillation_includes_preflight_payload(tmp_path, monkeypatch):
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
    baseline = generator.generate(project, scan, evidence)
    provider = ModelProviderConfig(
        id="xunfei",
        name="xunfei",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="provider/model",
        api_shape="chat_completions",
        api_key="secret",
    )

    monkeypatch.setattr(
        sdk_distillation,
        "_load_oss_skill_bundle",
        lambda: ("oss-skill-bundle", []),
    )
    monkeypatch.setattr(
        sdk_distillation,
        "_build_preflight_context",
        lambda project: {
            "target_project": str(project.root_path),
            "top_tree_preview": ["a", "b"],
            "java_files_preview": ["A.java"],
            "markdown_files_preview": ["README.md"],
            "pom_files": ["pom.xml"],
        },
    )

    captured: dict[str, object] = {}

    async def fake_request(provider_config, payload):
        captured["payload"] = payload
        return {
            "rules": [rule.model_dump(mode="json") for rule in baseline.rules],
            "skill_markdown": baseline.skill_markdown,
            "execution_note": "ok",
        }

    monkeypatch.setattr(sdk_distillation, "_request_orchestrated_distillation", fake_request)

    asyncio.run(
        sdk_distillation.run_agent_distillation(
            provider_config=provider,
            project=project,
            scan=scan,
            evidence=evidence,
            baseline=baseline,
        )
    )

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert "preflight" in payload
    assert payload["preflight"]["java_files_preview"] == ["A.java"]
