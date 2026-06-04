from fastapi.testclient import TestClient

from app.main import app


def test_mcp_server_crud_and_toggle_flow():
    client = TestClient(app)

    create_response = client.post(
        "/mcp-servers",
        json={
            "name": "Docs Gateway",
            "description": "企业内部文档入口",
            "transport": "streamable_http",
            "scope": "project",
            "enabled": False,
            "endpoint": "https://docs.example.com/mcp",
            "args": [],
            "env": [{"key": "AUTH_MODE", "value": "bearer"}],
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["id"] == "mcp_docs_gateway"
    assert created["status"] == "idle"

    list_response = client.get("/mcp-servers")
    assert list_response.status_code == 200
    assert any(item["id"] == "mcp_docs_gateway" for item in list_response.json())

    detail_response = client.get("/mcp-servers/mcp_docs_gateway")
    assert detail_response.status_code == 200
    assert detail_response.json()["endpoint"] == "https://docs.example.com/mcp"

    toggle_response = client.post("/mcp-servers/mcp_docs_gateway/toggle", json={"enabled": True})
    assert toggle_response.status_code == 200
    assert toggle_response.json()["enabled"] is True
    assert toggle_response.json()["status"] == "connected"


def test_mcp_server_sources_are_visible_in_capability_sources():
    client = TestClient(app)
    create_response = client.post(
        "/mcp-servers",
        json={
            "name": "Context Search",
            "description": "检索上下文服务",
            "transport": "stdio",
            "scope": "global",
            "enabled": True,
            "command": "npx",
            "args": ["context-search-mcp@latest"],
            "env": [],
        },
    )
    assert create_response.status_code == 200

    sources_response = client.get("/graph/capability-sources")
    assert sources_response.status_code == 200
    body = sources_response.json()
    match = next((item for item in body if item["source_type"] == "mcp_server" and item["name"] == "Context Search"), None)
    assert match is not None
    assert match["metadata"]["transport"] == "stdio"
    assert match["suggested_kind"] == "service"

