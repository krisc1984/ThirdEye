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
    assert get_response.json()["knowledge_root_path"] is None


def test_knowledge_workspace_settings_and_project_override(tmp_path: Path):
    client = TestClient(app)
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    project_knowledge_root = tmp_path / "project-knowledge"
    project_knowledge_root.mkdir()

    create_response = client.post(
        "/projects",
        json={"root_path": str(FIXTURE), "extra_ignore_patterns": [], "name": "Knowledge Project"},
    )
    assert create_response.status_code == 200
    project = create_response.json()

    set_global = client.put("/knowledge-workspace", json={"root_path": str(knowledge_root)})
    assert set_global.status_code == 200
    assert set_global.json()["default_root_path"] == str(knowledge_root.resolve())

    get_binding = client.get(f"/knowledge-workspace/projects/{project['id']}")
    assert get_binding.status_code == 200
    assert get_binding.json()["effective_root_path"] == str(knowledge_root.resolve())
    assert get_binding.json()["scope"] == "global"

    set_project = client.put(
        f"/knowledge-workspace/projects/{project['id']}",
        json={"root_path": str(project_knowledge_root)},
    )
    assert set_project.status_code == 200
    assert set_project.json()["project_root_path"] == str(project_knowledge_root.resolve())
    assert set_project.json()["effective_root_path"] == str(project_knowledge_root.resolve())
    assert set_project.json()["scope"] == "project"


def test_knowledge_workspace_lists_and_uploads_files(tmp_path: Path):
    client = TestClient(app)
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    (knowledge_root / "README.md").write_text("# hello", encoding="utf-8")
    docs_dir = knowledge_root / "docs"
    docs_dir.mkdir()
    (docs_dir / "design.md").write_text("design", encoding="utf-8")

    set_global = client.put("/knowledge-workspace", json={"root_path": str(knowledge_root)})
    assert set_global.status_code == 200

    listing = client.get("/knowledge-workspace/files")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["root_path"] == str(knowledge_root.resolve())
    assert any(item["relative_path"] == "README.md" for item in payload["items"])
    assert any(item["relative_path"] == "docs/design.md" for item in payload["items"])

    search = client.get("/knowledge-workspace/files", params={"query": "design"})
    assert search.status_code == 200
    search_items = search.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["relative_path"] == "docs/design.md"

    upload = client.post(
        "/knowledge-workspace/files/upload",
        files=[("files", ("notes.txt", b"hello upload", "text/plain"))],
    )
    assert upload.status_code == 200
    assert "notes.txt" in upload.json()["uploaded_files"]
    assert (knowledge_root / "notes.txt").read_text(encoding="utf-8") == "hello upload"
