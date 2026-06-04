from fastapi.testclient import TestClient

from app.main import app
from app.model_providers.llm_client import LLMClient


def _seed_capability(client: TestClient, capability_id: str, action: str) -> None:
    response = client.post(
        "/graph/capabilities",
        json={
            "id": capability_id,
            "name": capability_id,
            "kind": "tool",
            "action": action,
        },
    )
    assert response.status_code == 200


def test_skill_graph_api_endpoints_happy_path():
    client = TestClient(app)

    assert client.get("/graph/capabilities").status_code == 200
    _seed_capability(client, "cap_fetch", "fetch")
    _seed_capability(client, "cap_render", "render")

    composite_response = client.post(
        "/graph/composites",
        json={
            "id": "comp_report",
            "name": "Report",
            "mode": "chain",
            "nodes": [
                {"id": "fetch", "capability_id": "cap_fetch", "order": 1},
                {"id": "render", "capability_id": "cap_render", "order": 2},
            ],
        },
    )
    assert composite_response.status_code == 200
    assert client.get("/graph/composites").status_code == 200

    composite_compile = client.post("/graph/composites/comp_report/compile")
    assert composite_compile.status_code == 200
    assert composite_compile.json()["ok"] is True

    playbook_response = client.post(
        "/graph/playbooks",
        json={
            "id": "graph_report",
            "name": "Graph Report",
            "version": "1.0.0",
            "entry_node_id": "review",
            "nodes": [
                {"id": "review", "type": "human_approval", "approval_label": "Review draft"},
                {"id": "run_report", "type": "composite", "composite_id": "comp_report"},
            ],
            "edges": [{"source": "review", "target": "run_report", "condition": "approve"}],
        },
    )
    assert playbook_response.status_code == 200
    assert client.get("/graph/playbooks").status_code == 200

    playbook_compile = client.post("/graph/playbooks/graph_report/compile")
    assert playbook_compile.status_code == 200
    compile_body = playbook_compile.json()
    assert compile_body["ok"] is False
    assert compile_body["errors"]


def test_skill_graph_run_and_approval_flow():
    client = TestClient(app)
    _seed_capability(client, "cap_publish", "render_weekly_report")

    playbook_response = client.post(
        "/graph/playbooks",
        json={
            "id": "graph_publish",
            "name": "Publish",
            "version": "1.0.0",
            "entry_node_id": "review",
            "nodes": [
                {"id": "review", "type": "human_approval", "approval_label": "Review draft"},
                {"id": "publish", "type": "capability", "capability_id": "cap_publish"},
            ],
            "edges": [{"source": "review", "target": "publish", "condition": "approve"}],
        },
    )
    assert playbook_response.status_code == 200

    run_response = client.post(
        "/graph/playbooks/graph_publish/runs",
        json={"input_payload": {"topic": "ThirdEye"}},
    )
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["status"] == "waiting_for_human"

    run_id = run_body["id"]
    detail_response = client.get(f"/graph/runs/{run_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == run_id

    approval_id = run_body["approvals"][0]["approval_id"]
    approval_response = client.post(
        f"/graph/runs/{run_id}/approvals/{approval_id}",
        json={"approved": True, "decided_by": "tester"},
    )
    assert approval_response.status_code == 200
    approval_body = approval_response.json()
    assert approval_body["status"] == "succeeded"


def test_skill_graph_events_endpoint_replays_snapshot():
    client = TestClient(app)
    _seed_capability(client, "cap_publish", "render_weekly_report")

    client.post(
        "/graph/playbooks",
        json={
            "id": "graph_events",
            "name": "Events",
            "version": "1.0.0",
            "entry_node_id": "publish",
            "nodes": [{"id": "publish", "type": "capability", "capability_id": "cap_publish"}],
            "edges": [],
        },
    )
    run_response = client.post(
        "/graph/playbooks/graph_events/runs",
        json={"input_payload": {"topic": "snapshot"}},
    )
    run_id = run_response.json()["id"]

    with client.stream("GET", f"/graph/runs/{run_id}/events?replay_only=true") as events_response:
        assert events_response.status_code == 200
        chunks = []
        for chunk in events_response.iter_text():
            chunks.append(chunk)
            if '"event_type":"snapshot"' in chunk:
                break
    assert any('"event_type":"snapshot"' in chunk for chunk in chunks)


def test_capability_crud_endpoints():
    client = TestClient(app)

    create_response = client.post(
        "/graph/capabilities",
        json={
            "id": "cap_agent_brief",
            "name": "Agent Brief",
            "kind": "agent",
            "action": "agent.brief",
            "description": "生成任务简报",
            "config": {"mode": "single_turn"},
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "retry_policy": {"max_attempts": 2, "backoff_seconds": 1, "retry_on": ["timeout"]},
            "enabled": True,
        },
    )
    assert create_response.status_code == 200

    detail_response = client.get("/graph/capabilities/cap_agent_brief")
    assert detail_response.status_code == 200
    assert detail_response.json()["kind"] == "agent"

    update_response = client.put(
        "/graph/capabilities/cap_agent_brief",
        json={
            **detail_response.json(),
            "description": "更新后的任务简报能力",
            "enabled": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "更新后的任务简报能力"
    assert update_response.json()["enabled"] is False

    delete_response = client.delete("/graph/capabilities/cap_agent_brief")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
    assert client.get("/graph/capabilities/cap_agent_brief").status_code == 404


def test_capability_delete_rejects_when_referenced():
    client = TestClient(app)
    _seed_capability(client, "cap_fetch", "fetch")
    composite_response = client.post(
        "/graph/composites",
        json={
            "id": "comp_fetch_only",
            "name": "Fetch Only",
            "mode": "chain",
            "nodes": [{"id": "fetch", "capability_id": "cap_fetch", "order": 1}],
        },
    )
    assert composite_response.status_code == 200

    delete_response = client.delete("/graph/capabilities/cap_fetch")
    assert delete_response.status_code == 409
    assert "still referenced" in delete_response.json()["detail"]


def test_composite_crud_endpoints():
    client = TestClient(app)
    _seed_capability(client, "cap_fetch", "fetch")

    create_response = client.post(
        "/graph/composites",
        json={
            "id": "comp_fetch_only",
            "name": "Fetch Only",
            "mode": "chain",
            "description": "单步抓取链路",
            "nodes": [{"id": "fetch", "capability_id": "cap_fetch", "order": 1, "input_mapping": {}}],
        },
    )
    assert create_response.status_code == 200

    detail_response = client.get("/graph/composites/comp_fetch_only")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Fetch Only"

    update_response = client.put(
        "/graph/composites/comp_fetch_only",
        json={
            **detail_response.json(),
            "description": "更新后的链路描述",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "更新后的链路描述"

    delete_response = client.delete("/graph/composites/comp_fetch_only")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"


def test_composite_delete_rejects_when_referenced():
    client = TestClient(app)
    _seed_capability(client, "cap_fetch", "fetch")
    composite_response = client.post(
        "/graph/composites",
        json={
            "id": "comp_fetch_only",
            "name": "Fetch Only",
            "mode": "chain",
            "nodes": [{"id": "fetch", "capability_id": "cap_fetch", "order": 1, "input_mapping": {}}],
        },
    )
    assert composite_response.status_code == 200
    playbook_response = client.post(
        "/graph/playbooks",
        json={
            "id": "graph_fetch_only",
            "name": "Fetch Graph",
            "version": "1.0.0",
            "entry_node_id": "start",
            "nodes": [{"id": "start", "type": "composite", "composite_id": "comp_fetch_only"}],
            "edges": [],
        },
    )
    assert playbook_response.status_code == 200

    delete_response = client.delete("/graph/composites/comp_fetch_only")
    assert delete_response.status_code == 409
    assert "still referenced" in delete_response.json()["detail"]


def test_playbook_crud_endpoints():
    client = TestClient(app)
    _seed_capability(client, "cap_fetch", "fetch")

    create_response = client.post(
        "/graph/playbooks",
        json={
            "id": "graph_fetch_only",
            "name": "Fetch Graph",
            "version": "1.0.0",
            "description": "单节点剧本",
            "entry_node_id": "start",
            "nodes": [{"id": "start", "type": "capability", "capability_id": "cap_fetch", "config": {}}],
            "edges": [],
        },
    )
    assert create_response.status_code == 200

    detail_response = client.get("/graph/playbooks/graph_fetch_only")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Fetch Graph"

    update_response = client.put(
        "/graph/playbooks/graph_fetch_only",
        json={
            **detail_response.json(),
            "description": "更新后的顶层剧本描述",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "更新后的顶层剧本描述"

    delete_response = client.delete("/graph/playbooks/graph_fetch_only")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"


def test_capability_draft_falls_back_to_template_without_provider():
    client = TestClient(app)
    response = client.post(
        "/graph/capabilities/draft",
        json={
            "kind": "service",
            "name": "发布回调",
            "description": "调用内部发布服务回调接口",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "deterministic"
    assert body["capability"]["kind"] == "service"
    assert body["capability"]["config"]["method"] == "POST"


def test_capability_draft_uses_llm_when_provider_selected(monkeypatch):
    client = TestClient(app)
    provider_response = client.post(
        "/model-providers",
        json={
            "id": "draft-provider",
            "name": "Draft Provider",
            "provider_type": "openai",
            "model": "gpt-5.4",
            "api_shape": "responses",
        },
    )
    assert provider_response.status_code == 200

    async def _fake_generate(self, config, payload):
        assert config.id == "draft-provider"
        assert payload["kind"] == "tool"
        return {
            "id": "cap_tool_publish_summary",
            "action": "publish.summary",
            "description": "生成并发布摘要",
            "config": {"transport": "http", "timeout_seconds": 15},
            "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"published": {"type": "boolean"}}},
            "retry_policy": {"max_attempts": 2, "backoff_seconds": 1, "retry_on": ["timeout"]},
        }

    monkeypatch.setattr(LLMClient, "generate_capability_draft", _fake_generate)

    response = client.post(
        "/graph/capabilities/draft",
        json={
            "kind": "tool",
            "name": "Publish Summary",
            "description": "负责发布摘要",
            "provider_id": "draft-provider",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["execution_mode"] == "llm"
    assert body["resolved_provider_id"] == "draft-provider"
    assert body["capability"]["action"] == "publish.summary"


def test_capability_sources_lists_skills_agents_tools_and_mcp():
    client = TestClient(app)
    create_response = client.post(
        "/mcp-servers",
        json={
            "name": "Local MCP",
            "description": "用于验证 capability source",
            "transport": "stdio",
            "scope": "global",
            "enabled": True,
            "command": "npx",
            "args": ["local-mcp@latest"],
            "env": [],
        },
    )
    assert create_response.status_code == 200
    response = client.get("/graph/capability-sources")
    assert response.status_code == 200
    body = response.json()
    source_types = {item["source_type"] for item in body}
    assert "skill" in source_types
    assert "agent" in source_types
    assert "tool" in source_types
    assert "mcp_server" in source_types
    assert any(item["source_type"] == "tool" and item["source_id"] == "tavily_web_search" for item in body)


def test_capability_draft_from_agent_source():
    client = TestClient(app)
    response = client.post(
        "/graph/capabilities/draft",
        json={
            "kind": "agent",
            "name": "代码评审 Agent",
            "description": "基于现有业务 Agent 生成原子注册草稿",
            "source_type": "agent",
            "source_id": "code-review-agent",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capability"]["source"]["source_type"] == "agent"
    assert body["capability"]["config"]["agent_id"] == "code-review-agent"
    assert body["capability"]["action"] == "agent.code_review_agent"


def test_capability_draft_from_tool_source():
    client = TestClient(app)
    response = client.post(
        "/graph/capabilities/draft",
        json={
            "kind": "tool",
            "name": "读取文件",
            "source_type": "tool",
            "source_id": "read_file",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capability"]["source"]["source_type"] == "tool"
    assert body["capability"]["config"]["tool_name"] == "read_file"
    assert body["capability"]["action"] == "read_file"
