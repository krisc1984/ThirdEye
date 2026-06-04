from fastapi.testclient import TestClient

from app.main import app


def test_tavily_settings_defaults_and_update():
    client = TestClient(app)

    get_response = client.get("/settings/tavily")
    assert get_response.status_code == 200
    assert get_response.json() == {"api_key": None, "enabled": False}

    update_response = client.put(
        "/settings/tavily",
        json={"api_key": "tvly-secret", "enabled": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is True
    assert update_response.json()["api_key"] == "********"

    roundtrip_response = client.get("/settings/tavily")
    assert roundtrip_response.status_code == 200
    assert roundtrip_response.json()["enabled"] is True
    assert roundtrip_response.json()["api_key"] == "********"

