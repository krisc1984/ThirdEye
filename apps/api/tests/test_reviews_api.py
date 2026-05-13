import contextlib
import json
import importlib
import threading
import time
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from app.agents.sdk_chat import InvalidResumeStateError, _select_tool_choice
from app.agents.sdk_runtime import TextAgentRunResult
from app.agents.tool import (
    build_agent_tools,
    replace_in_file_failure_error,
    normalize_allowed_roots,
    read_allowed_file_payload,
    append_text_file,
    validate_tool_json_arguments,
    WRITE_FILE_CHUNK_SPEC,
    REPLACE_IN_FILE_SPEC,
)
from app.core.config import settings
from app.main import app
from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from scripts.skill_agent import SkillLoader, run_edit, run_list_skills


def _seed_playbook(client: TestClient) -> str:
    project_root = Path(__file__).parent / "fixtures" / "sample_project"
    project = client.post(
        "/projects",
        json={"root_path": str(project_root), "extra_ignore_patterns": [], "name": "Sample Project"},
    ).json()
    metadata = client.post("/playbooks/distill", json={"project_id": project["id"]}).json()
    return metadata["id"]


def _seed_project(client: TestClient, name: str) -> dict:
    project_root = Path(__file__).parent / "fixtures" / "sample_project"
    return client.post(
        "/projects",
        json={"root_path": str(project_root), "extra_ignore_patterns": [], "name": name},
    ).json()


def _seed_default_provider(client: TestClient) -> None:
    client.post(
        "/model-providers",
        json={
            "id": "xunfei",
            "name": "Default Provider",
            "provider_type": "openai",
            "model": "provider/default-model",
            "api_shape": "responses",
            "api_key": "secret",
        },
    )


def test_create_and_get_review():
    client = TestClient(app)
    playbook_id = _seed_playbook(client)

    create = client.post(
        "/reviews",
        json={
            "playbook_id": playbook_id,
            "proposal": "Introduce a caching layer without detailing module impact.",
            "mode": "standard",
        },
    )

    assert create.status_code == 200
    body = create.json()
    assert body["playbook_id"] == playbook_id
    assert body["overall_judgement"] in {"通过", "有条件通过", "建议修改后再评审", "不建议采用"}
    assert body["required_validation"]

    fetched = client.get(f"/reviews/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_create_review_rejects_missing_playbook():
    client = TestClient(app)

    response = client.post(
        "/reviews",
        json={"playbook_id": "pb_missing", "proposal": "Do something", "mode": "quick"},
    )

    assert response.status_code == 404


def test_create_review_falls_back_when_provider_call_fails(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    client.post(
        "/model-providers",
        json={
            "id": "router-api",
            "name": "Router",
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "secret",
        },
    )

    original_run_review = __import__("app.api.reviews", fromlist=["run_review"]).run_review

    async def flaky_review(*args, **kwargs):
        if kwargs.get("provider_config") is not None:
            raise RuntimeError("Example Domain")
        return await original_run_review(*args, **kwargs)

    monkeypatch.setattr("app.api.reviews.run_review", flaky_review)

    response = client.post(
        "/reviews",
        json={
            "playbook_id": playbook_id,
            "proposal": "Introduce a caching layer without detailing module impact.",
            "mode": "standard",
            "model_provider_id": "router-api",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert "fell back" in body["execution_note"]


def test_review_session_message_uses_skill_agent(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    selected_project = _seed_project(client, "Code Space")
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": selected_project["id"],
            "mode": "standard",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    async def fake_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
    ):
        assert name == "ThirdEye Review Conversation Agent"
        assert "项目空间目录地址" in user_input
        assert selected_project["root_path"] in user_input
        assert "资料库目录地址" in user_input
        assert "评审规则" in user_input
        assert "规则说明" in user_input
        assert "当前用户消息" in user_input
        assert "请帮我评审这个方案" in user_input
        assert "必须始终使用中文回复" in instructions
        assert "必须优先使用可用的 function tools 主动读取或检索信息" in instructions
        assert selected_project["root_path"] in instructions
        assert tools is not None
        tool_names = {tool.name for tool in tools}
        assert tool_names == {
            "bash",
            "read_file",
            "write_file_chunk",
            "replace_in_file",
            "load_skill",
            "list_skills",
        }
        assert session is not None
        assert model_settings.tool_choice == "auto"
        return TextAgentRunResult(output_text="这是 skill agent 的回复")

    client.post(
        "/model-providers",
        json={
            "id": "router-api",
            "name": "Router",
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "secret",
        },
    )
    client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": selected_project["id"],
            "mode": "standard",
            "model_provider_id": "router-api",
        },
    )

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "请帮我评审这个方案"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["latest_summary"] == "这是 skill agent 的回复"
    assert body["messages"][-1]["role"] == "assistant"
    assert body["messages"][-1]["content"] == "这是 skill agent 的回复"


def test_review_session_stop_cancels_running_agent(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "mode": "standard",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    started = threading.Event()

    async def slow_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
    ):
        started.set()
        await __import__("asyncio").sleep(10)
        return TextAgentRunResult(output_text="不会返回")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", slow_run_text_agent)

    result_holder: dict[str, object] = {}

    def send_message() -> None:
        result_holder["response"] = client.post(
            f"/reviews/sessions/{session_id}/messages",
            json={"message": "请启动一次长任务"},
        )

    worker = threading.Thread(target=send_message)
    worker.start()
    assert started.wait(timeout=2)
    time.sleep(0.2)

    stop_response = client.post(f"/reviews/sessions/{session_id}/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "idle"

    worker.join(timeout=5)
    assert not worker.is_alive()
    send_response = result_holder["response"]
    assert send_response.status_code == 409
    assert send_response.json()["detail"] == "review session cancelled"

    session_response = client.get(f"/reviews/sessions/{session_id}")
    assert session_response.status_code == 200
    body = session_response.json()
    assert body["status"] == "idle"
    assert body["execution_note"] == "agent run cancelled by user"


def test_function_tools_enforce_allowed_paths(tmp_path: Path):
    project_root = tmp_path / "project"
    kb_root = tmp_path / "kb"
    outside_root = tmp_path / "outside"
    project_root.mkdir()
    kb_root.mkdir()
    outside_root.mkdir()
    target_file = project_root / "summary.md"
    target_file.write_text("hello project", encoding="utf-8")
    (outside_root / "secret.txt").write_text("secret", encoding="utf-8")

    allowed_roots = normalize_allowed_roots(str(project_root), str(kb_root))
    output = read_allowed_file_payload(
        str(target_file),
        allowed_roots=allowed_roots,
        default_root=allowed_roots[0],
    )
    assert "hello project" in output

    with pytest.raises(ValueError, match="allowed roots"):
        read_allowed_file_payload(
            str(outside_root / "secret.txt"),
            allowed_roots=allowed_roots,
            default_root=allowed_roots[0],
        )


def test_function_tools_allow_apps_api_skills_directory():
    project_root = Path("F:\\codebaby\\ThirdEye")
    kb_root = Path("F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1")
    skills_root = Path("F:\\codebaby\\ThirdEye\\apps\\api\\skills").resolve()

    allowed_roots = normalize_allowed_roots(str(project_root), str(kb_root))

    assert skills_root in allowed_roots
    resolved_payload = read_allowed_file_payload(
        str(skills_root / "pdf" / "SKILL.md"),
        allowed_roots=allowed_roots,
        default_root=allowed_roots[0],
    )
    assert "PDF" in resolved_payload or "pdf" in resolved_payload


def test_agent_tools_include_skill_operations():
    tools = build_agent_tools(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )
    tool_names = {tool.name for tool in tools}
    assert "load_skill" in tool_names
    assert "list_skills" in tool_names
    assert "write_file_chunk" in tool_names
    assert "replace_in_file" in tool_names


def test_agent_tools_support_plain_text_replace_file_payloads(tmp_path: Path):
    project_root = tmp_path / "project"
    kb_root = tmp_path / "kb"
    project_root.mkdir()
    kb_root.mkdir()
    target_file = project_root / "notes.md"

    initial_content = '# 标题\n\n他说："hello"\n```json\n{"a": 1}\n```\n'
    write_result = append_text_file(
        str(target_file),
        initial_content,
        project_root,
        [project_root, kb_root],
        overwrite=True,
    )
    assert "Wrote" in write_result
    assert target_file.read_text(encoding="utf-8") == initial_content

    old_text = '他说："hello"'
    new_text = '他说："world"\n并保留第二行'
    edit_result = run_edit(str(target_file), old_text, new_text, project_root, [project_root, kb_root])
    assert edit_result == f"Edited {target_file}"
    updated = target_file.read_text(encoding="utf-8")
    assert new_text in updated


def test_agent_tools_support_chunked_file_writes(tmp_path: Path):
    project_root = tmp_path / "project"
    kb_root = tmp_path / "kb"
    project_root.mkdir()
    kb_root.mkdir()
    target_file = project_root / "chunked.md"

    overwrite_result = append_text_file(
        str(target_file),
        "# Header\n",
        project_root,
        [project_root, kb_root],
        overwrite=True,
    )
    append_result = append_text_file(
        str(target_file),
        "Body\n",
        project_root,
        [project_root, kb_root],
        overwrite=False,
    )

    assert "Wrote" in overwrite_result
    assert "Appended" in append_result
    assert target_file.read_text(encoding="utf-8") == "# Header\nBody\n"


def test_agent_instructions_require_strict_write_tools():
    from app.agents.sdk_chat import _build_agent_instructions

    instructions = _build_agent_instructions(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )
    assert "业务智能体：代码评审 Agent" in instructions
    assert "专业的代码评审智能体" in instructions
    assert "只能使用 write_file_chunk 或 replace_in_file" in instructions
    assert "write_file_chunk" in instructions
    assert "调用 write_file_chunk 时" in instructions
    assert "调用 replace_in_file 时" in instructions
    assert "write_file" not in instructions.replace("write_file_chunk", "")
    assert "edit_file" not in instructions
    assert "技能目录" in instructions


def test_agent_instructions_use_active_business_agent_prompt():
    from app.agents.sdk_chat import _build_agent_instructions
    from app.services.business_agents import BusinessAgentService
    from app.services.storage import JsonStorage

    service = BusinessAgentService(JsonStorage(settings.data_dir))
    service.activate_agent("test-review-agent")

    instructions = _build_agent_instructions(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )

    assert "业务智能体：测试评审 Agent" in instructions
    assert "你是专业的测试评审智能体" in instructions


def test_agent_tools_use_strict_write_tool_names():
    tools = build_agent_tools(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )
    tool_map = {tool.name: tool for tool in tools}
    assert "write_file_chunk" in tool_map
    assert "replace_in_file" in tool_map
    assert "write_file" not in tool_map
    assert "edit_file" not in tool_map


def test_agent_write_tools_only_expose_plain_text_fields():
    tools = build_agent_tools(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )
    tool_map = {tool.name: tool for tool in tools}

    chunk_schema = tool_map["write_file_chunk"].params_json_schema
    replace_schema = tool_map["replace_in_file"].params_json_schema

    assert set(chunk_schema["properties"]) == {"path", "content", "mode"}
    assert chunk_schema["required"] == ["path", "content", "mode"]

    assert set(replace_schema["properties"]) == {"path", "old_text", "new_text"}
    assert replace_schema["required"] == ["path", "old_text", "new_text"]


def test_agent_write_tool_failure_messages_are_actionable_for_empty_arguments():
    tools = build_agent_tools(
        project_root_path="F:\\codebaby\\ThirdEye",
        knowledge_base_path="F:\\codebaby\\ThirdEye\\data\\playbooks\\pb_azure_v1",
    )
    tool_map = {tool.name: tool for tool in tools}

    class _DummyCtx:
        def __init__(self, tool_name: str, tool_arguments: str):
            self.tool_name = tool_name
            self.tool_arguments = tool_arguments

    replace_message = replace_in_file_failure_error(
        _DummyCtx("replace_in_file", ""),
        Exception("invalid"),
    )

    assert "called with empty arguments" in replace_message
    assert '"old_text":"...","new_text":"..."' in replace_message


def test_validate_tool_json_arguments_rejects_missing_required_fields():
    payload, error = validate_tool_json_arguments(
        tool_name="replace_in_file",
        tool_arguments='{"path":"a.txt","old_text":"old"}',
        spec=REPLACE_IN_FILE_SPEC,
    )
    assert payload is None
    assert error is not None
    assert "arguments are invalid" in error
    assert "new_text" in error


def test_validate_tool_json_arguments_accepts_chunk_write_json():
    payload, error = validate_tool_json_arguments(
        tool_name="write_file_chunk",
        tool_arguments='{"path":"a.txt","content":"content","mode":"append"}',
        spec=WRITE_FILE_CHUNK_SPEC,
    )
    assert error is None
    assert payload == {
        "path": "a.txt",
        "content": "content",
        "mode": "append",
    }



def test_agent_tools_use_apps_api_skills_directory():
    client = TestClient(app)
    response = client.get("/skills")
    assert response.status_code == 200
    skill_names = {item["name"] for item in response.json()}
    assert "pdf" in skill_names


def test_list_skills_output_includes_all_skill_names():
    client = TestClient(app)
    response = client.get("/skills")
    assert response.status_code == 200
    skill_names = [item["name"] for item in response.json()]
    assert "oss-skill" in skill_names
    assert "pdf" in skill_names


def test_run_list_skills_output_contains_oss_skill():
    loader = SkillLoader(Path("F:\\codebaby\\ThirdEye\\apps\\api\\skills"))
    output = run_list_skills(loader)
    assert "oss-skill" in output
    assert "pdf" in output
    assert "Use load_skill(name) to inspect one skill in detail." in output


def test_review_session_chat_completions_provider_does_not_attach_shell_tool(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    selected_project = _seed_project(client, "Chat Provider Space")

    client.post(
        "/model-providers",
        json={
            "id": "router-api",
            "name": "Router",
            "provider_type": "openai_compatible",
            "base_url": "https://example.com/v1",
            "model": "provider/model",
            "api_shape": "chat_completions",
            "api_key": "secret",
        },
    )
    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": selected_project["id"],
            "mode": "standard",
            "model_provider_id": "router-api",
        },
    )
    assert session.status_code == 200

    async def fake_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
    ):
        assert provider_config is not None
        assert provider_config.api_shape == "chat_completions"
        assert tools is not None
        assert {tool.name for tool in tools} == {
            "bash",
            "read_file",
            "write_file_chunk",
            "replace_in_file",
            "load_skill",
            "list_skills",
        }
        assert model_settings.tool_choice == "auto"
        return TextAgentRunResult(output_text="chat_completions provider reply")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session.json()['id']}/messages",
        json={"message": "请继续评审"},
    )

    assert response.status_code == 200
    assert response.json()["latest_summary"] == "chat_completions provider reply"


def test_review_session_without_available_provider_returns_graceful_message(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "mode": "standard",
            "model_provider_id": "missing-provider",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "请继续评审"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["resolved_provider_id"] is None
    assert "没有可用的大模型配置" in body["latest_summary"]


def test_review_session_provider_failure_returns_graceful_message(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "mode": "standard",
            "model_provider_id": "xunfei",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    async def failing_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
    ):
        raise RuntimeError("upstream 500 from provider")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", failing_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "请继续评审"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["resolved_provider_id"] is None
    assert "当前不可用" in body["latest_summary"]
    assert "upstream 500 from provider" in body["execution_note"]


def test_review_session_oss_skill_local_distill_request_shortcuts_to_preflight(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    selected_project = _seed_project(client, "Code Space")
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": selected_project["id"],
            "mode": "standard",
            "model_provider_id": "xunfei",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    monkeypatch.setattr(
        "app.agents.sdk_chat._maybe_run_oss_skill_preflight",
        lambda query: "# preflight result\n\nbackend shortcut hit" if "oss-skill" in query else None,
    )

    async def should_not_run_text_agent(**kwargs):
        raise AssertionError("run_text_agent should not be called for deterministic oss-skill preflight shortcut")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", should_not_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": '请调用 oss-skill 蒸馏 "D:\\python_project\\code-review" 项目并输出结果'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["resolved_provider_id"] is None
    assert "backend shortcut hit" in body["latest_summary"]
    assert body["execution_note"] == "Handled by deterministic oss-skill preflight shortcut."


def test_review_session_interrupted_run_sets_resume_checkpoint(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
    )
    session_id = session.json()["id"]

    async def interrupted_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
        resume_state=None,
    ):
        raise __import__("app.agents.sdk_runtime", fromlist=["AgentResumeError"]).AgentResumeError(
            "recoverable failure",
            resume_state_json={"$schemaVersion": "1.10", "mock": True},
        )

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", interrupted_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "请继续执行任务"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resume_available"] is True
    assert body["resume_reason"] == "runtime_error"
    assert "已保存断点" in body["messages"][-1]["content"]


def test_review_session_resume_endpoint_clears_checkpoint(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
    )
    session_id = session.json()["id"]

    async def interrupted_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
        resume_state=None,
    ):
        if resume_state is None:
            raise __import__("app.agents.sdk_runtime", fromlist=["AgentResumeError"]).AgentResumeError(
                "recoverable failure",
                resume_state_json={"$schemaVersion": "1.10", "mock": True},
            )
        return TextAgentRunResult(output_text="已从断点继续执行完成")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", interrupted_run_text_agent)
    
    async def fake_resume_agent_chat_turn(
        *,
        session_store,
        session_id,
        playbook,
        provider_config,
    ):
        session_store.clear_resume_state(session_id)
        return __import__("app.agents.sdk_chat", fromlist=["AgentChatTurnResult"]).AgentChatTurnResult(
            assistant_text="已从断点继续执行完成",
            review=None,
            execution_mode="llm",
            resolved_provider_id="xunfei",
            execution_note="resume ok",
        )

    monkeypatch.setattr("app.api.reviews.resume_agent_chat_turn", fake_resume_agent_chat_turn)

    first_response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "先制造一个可恢复断点"},
    )
    assert first_response.status_code == 200
    assert first_response.json()["resume_available"] is True

    response = client.post(f"/reviews/sessions/{session_id}/resume")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_available"] is False
    assert body["messages"][-1]["content"] == "已从断点继续执行完成"


def test_review_session_resume_invalid_checkpoint_returns_409(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
    )
    session_id = session.json()["id"]

    client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "先制造一个可恢复断点"},
    )

    storage = __import__("app.services.storage", fromlist=["JsonStorage"]).JsonStorage(
        __import__("app.core.config", fromlist=["settings"]).settings.data_dir
    )
    storage.save_json("review-session-resume", session_id, {"$schemaVersion": "1.10", "mock": True})
    session_record = storage.load_json("review-sessions", session_id)
    session_record["resume_available"] = True
    session_record["resume_reason"] = "runtime_error"
    storage.save_json("review-sessions", session_id, session_record)

    async def fake_resume_agent_chat_turn(
        *,
        session_store,
        session_id,
        playbook,
        provider_config,
    ):
        raise InvalidResumeStateError("保存的断点无效或已过期，无法继续恢复，请重新发起任务。")

    monkeypatch.setattr("app.api.reviews.resume_agent_chat_turn", fake_resume_agent_chat_turn)

    response = client.post(f"/reviews/sessions/{session_id}/resume")

    assert response.status_code == 409
    assert "断点无效" in response.json()["detail"]


def test_review_session_non_resumable_agent_error_does_not_create_checkpoint(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
    )
    session_id = session.json()["id"]

    async def non_resumable_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
        resume_state=None,
    ):
        raise __import__("app.agents.sdk_runtime", fromlist=["AgentResumeError"]).AgentResumeError(
            "upstream transient failure",
            resumable=False,
        )

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", non_resumable_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "触发一个普通失败"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resume_available"] is False
    assert body["resume_reason"] is None
    assert "当前不可用" in body["latest_summary"]


def test_review_session_resume_non_resumable_error_clears_checkpoint(monkeypatch):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    _seed_default_provider(client)

    session = client.post(
        "/reviews/sessions",
        json={"playbook_id": playbook_id, "mode": "standard", "model_provider_id": "xunfei"},
    )
    session_id = session.json()["id"]

    storage = __import__("app.services.storage", fromlist=["JsonStorage"]).JsonStorage(
        __import__("app.core.config", fromlist=["settings"]).settings.data_dir
    )
    storage.save_json("review-session-resume", session_id, {"$schemaVersion": "1.10", "current_agent": "mock"})
    session_record = storage.load_json("review-sessions", session_id)
    session_record["resume_available"] = True
    session_record["resume_reason"] = "tool_approval"
    storage.save_json("review-sessions", session_id, session_record)

    async def fake_resume_agent_chat_turn(
        *,
        session_store,
        session_id,
        playbook,
        provider_config,
    ):
        session_store.clear_resume_state(session_id)
        return __import__("app.agents.sdk_chat", fromlist=["AgentChatTurnResult"]).AgentChatTurnResult(
            assistant_text="Default Provider 在继续执行时返回了不可恢复错误，当前断点已清除。\n\n请重新发送任务，或切换到其他模型配置后再试。",
            review=None,
            execution_mode="deterministic",
            resolved_provider_id=None,
            execution_note="LLM resume failed: upstream transient failure",
        )

    monkeypatch.setattr("app.api.reviews.resume_agent_chat_turn", fake_resume_agent_chat_turn)

    response = client.post(f"/reviews/sessions/{session_id}/resume")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_available"] is False
    assert "不可恢复错误" in body["latest_summary"]


def test_review_session_event_bus_encodes_sse_payload():
    from app.services.review_session_events import encode_sse_event, review_session_events

    session_id = "rs_test_sse"
    event = review_session_events.publish(
        session_id,
        "tool.start",
        {
            "message": {
                "id": "msg_test",
                "role": "tool",
                "content": "write_file_chunk 调用中",
                "tool_name": "write_file_chunk",
                "tool_call_id": "call_test_sse",
                "tool_arguments": '{"path":"a.txt"}',
                "tool_result": None,
                "created_at": "2026-05-11T00:00:00",
            }
        },
    )

    encoded = encode_sse_event(event)
    assert encoded.startswith("event: tool.start\n")
    assert '"session_id": "rs_test_sse"' in encoded
    assert '"tool_call_id": "call_test_sse"' in encoded


def test_local_agents_tool_json_repair_helpers():
    src_root = Path(__file__).resolve().parents[3] / "src"
    sys.path.insert(0, str(src_root))
    try:
        sys.modules.pop("agents.tool", None)
        sys.modules.pop("agents", None)
        module = importlib.import_module("agents.tool")

        repaired_from_fence = module._load_function_tool_json_with_repair('```json\n{"a": 2, "b": 3}\n```')
        assert repaired_from_fence == {"a": 2, "b": 3}

        repaired_from_trailing_comma = module._load_function_tool_json_with_repair('{"a": 4, "b": 5,')
        assert repaired_from_trailing_comma == {"a": 4, "b": 5}

        repaired_from_single_quotes = module._load_function_tool_json_with_repair("{'a': 6, 'b': 7}")
        assert repaired_from_single_quotes == {"a": 6, "b": 7}
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(src_root))


def test_tool_choice_is_required_for_file_and_skill_requests():
    assert _select_tool_choice("请读取 project-summary.md 并总结") == "required"
    assert _select_tool_choice("请修改这个文件，删除这一行") == "required"
    assert _select_tool_choice("请先列出技能，再加载 skill") == "required"
    assert _select_tool_choice("请读取这个 PDF 并总结内容") == "required"
    assert _select_tool_choice("帮我做一次技术评审总结") == "auto"


def test_review_session_uses_effective_knowledge_workspace_in_agent_prompt(monkeypatch, tmp_path: Path):
    client = TestClient(app)
    playbook_id = _seed_playbook(client)
    selected_project = _seed_project(client, "Knowledge Space")
    _seed_default_provider(client)

    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    update_binding = client.put(
        f"/knowledge-workspace/projects/{selected_project['id']}",
        json={"root_path": str(knowledge_root)},
    )
    assert update_binding.status_code == 200

    session = client.post(
        "/reviews/sessions",
        json={
            "playbook_id": playbook_id,
            "project_id": selected_project["id"],
            "mode": "standard",
            "model_provider_id": "xunfei",
        },
    )
    assert session.status_code == 200
    session_id = session.json()["id"]

    async def fake_run_text_agent(
        *,
        name,
        instructions,
        user_input,
        provider_config,
        session=None,
        tools=None,
        model_settings=None,
    ):
        assert str(knowledge_root.resolve()) in user_input
        assert str(knowledge_root.resolve()) in instructions
        return TextAgentRunResult(output_text="ok")

    monkeypatch.setattr("app.agents.sdk_chat.run_text_agent", fake_run_text_agent)

    response = client.post(
        f"/reviews/sessions/{session_id}/messages",
        json={"message": "请读取资料区文件并总结"},
    )
    assert response.status_code == 200
    assert response.json()["latest_summary"] == "ok"
