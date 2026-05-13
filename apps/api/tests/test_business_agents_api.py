from fastapi.testclient import TestClient

from app.main import app


def test_business_agents_bootstrap_list_and_activate():
    client = TestClient(app)

    listed = client.get("/agent-configs")
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) >= 3
    assert any(item["id"] == "code-review-agent" for item in payload)
    assert sum(1 for item in payload if item["is_default"]) == 1

    activate = client.post("/agent-configs/test-review-agent/activate", json={"id": "test-review-agent"})
    assert activate.status_code == 200
    assert activate.json()["id"] == "test-review-agent"
    assert activate.json()["is_default"] is True
    assert activate.json()["status"] == "active"

    relisted = client.get("/agent-configs")
    assert relisted.status_code == 200
    next_payload = relisted.json()
    assert sum(1 for item in next_payload if item["is_default"]) == 1
    assert next(item for item in next_payload if item["id"] == "test-review-agent")["status"] == "active"
    assert next(item for item in next_payload if item["id"] == "code-review-agent")["status"] == "draft"


def test_business_agents_create_and_update():
    client = TestClient(app)

    created = client.post(
        "/agent-configs",
        json={
            "id": "architecture-review-agent",
            "name": "架构评审 Agent",
            "description": "面向架构边界、依赖和演进策略的评审智能体。",
            "category": "architecture",
            "system_prompt": "检查模块边界、依赖方向和演进风险。",
            "status": "draft",
            "is_default": False,
        },
    )
    assert created.status_code == 200
    assert created.json()["id"] == "architecture-review-agent"

    updated = client.put(
        "/agent-configs/architecture-review-agent",
        json={
            "id": "architecture-review-agent",
            "name": "架构评审 Agent",
            "description": "更新后的描述。",
            "category": "architecture",
            "system_prompt": "优先检查系统边界与演进成本。",
            "status": "draft",
            "is_default": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "更新后的描述。"
    assert updated.json()["system_prompt"] == "优先检查系统边界与演进成本。"
