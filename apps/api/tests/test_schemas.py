import pytest
from pydantic import ValidationError

from app.schemas.model_provider import ModelProviderConfig
from app.schemas.playbook import PlaybookMetadata, PlaybookRule
from app.schemas.project import Project
from app.schemas.review import ReviewRequest


def test_project_slug_normalization():
    project = Project(
        id="proj_1",
        name="ThirdEye",
        root_path="F:/codebaby/ThirdEye",
        knowledge_root_path="F:/knowledge",
        slug="Third Eye MVP!",
    )

    assert project.slug == "third-eye-mvp"
    assert str(project.knowledge_root_path) == "F:\\knowledge"


def test_playbook_version_requires_semver():
    with pytest.raises(ValidationError):
        PlaybookMetadata(
            id="pb_1",
            project_id="proj_1",
            name="Playbook",
            version="v1",
            skill_path="data/playbooks/sample/playbook.skill.md",
            rules_path="data/playbooks/sample/rules.json",
            evidence_path="data/playbooks/sample/evidence.jsonl",
        )


def test_rule_rejects_blank_evidence_ids():
    with pytest.raises(ValidationError):
        PlaybookRule(
            id="rule_1",
            category="api",
            name="Rule",
            default_severity="major",
            description="A rule",
            evidence_ids=[""],
        )


def test_review_modes_are_limited():
    request = ReviewRequest(playbook_id="pb_1", proposal="方案", mode="strict")
    assert request.mode == "strict"

    with pytest.raises(ValidationError):
        ReviewRequest(playbook_id="pb_1", proposal="方案", mode="full")


def test_provider_api_shapes_are_limited():
    provider = ModelProviderConfig(
        id="provider_1",
        name="OpenAI",
        provider_type="openai",
        model="gpt-5.4",
        api_shape="responses",
    )
    assert provider.api_shape == "responses"

    with pytest.raises(ValidationError):
        ModelProviderConfig(
            id="provider_2",
            name="Bad",
            provider_type="openai",
            model="x",
            api_shape="completion",
        )


def test_openai_compatible_requires_base_url_and_chat_completions():
    with pytest.raises(ValidationError):
        ModelProviderConfig(
            id="provider_3",
            name="Router",
            provider_type="openai_compatible",
            model="provider/model",
            api_shape="chat_completions",
        )

    provider = ModelProviderConfig(
        id="provider_4",
        name="Router",
        provider_type="openai_compatible",
        base_url="https://example.com/v1",
        model="provider/model",
        api_shape="chat_completions",
        tracing_enabled=False,
    )

    assert provider.base_url == "https://example.com/v1"
