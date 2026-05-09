from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_scan_project_endpoint():
    client = TestClient(app)

    response = client.post(
        "/projects/scan",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": []},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scanned_files"] >= 3
    assert data["docs"] == ["README.md"]
    assert data["tests"] == ["tests/test_app.py"]


def test_scan_project_endpoint_rejects_missing_path():
    client = TestClient(app)

    response = client.post(
        "/projects/scan",
        json={"root_path": str(FIXTURE / "missing"), "extra_ignore_patterns": []},
    )

    assert response.status_code == 400


def test_create_list_and_get_project():
    client = TestClient(app)

    create_response = client.post(
        "/projects",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": [], "name": "Sample Project"},
    )
    assert create_response.status_code == 200
    project = create_response.json()
    assert project["name"] == "Sample Project"
    assert project["slug"] == "sample-project"

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    assert any(item["id"] == project["id"] for item in list_response.json())

    get_response = client.get(f"/projects/{project['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == project["id"]

