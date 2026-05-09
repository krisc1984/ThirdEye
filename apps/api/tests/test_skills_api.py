from fastapi.testclient import TestClient

from app.main import app


def test_list_skills():
    client = TestClient(app)
    response = client.get("/skills")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        assert "name" in body[0]
        assert "description" in body[0]
