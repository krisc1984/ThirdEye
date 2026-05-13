from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_save_markdown_file_to_knowledge_workspace(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    response = client.post(
        "/knowledge-workspace/files/save-text",
        json={
            "filename": "评审报告.md",
            "content": "# 报告\n\n内容",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["uploaded_files"] == ["评审报告.md"]
    assert (workspace / "评审报告.md").read_text(encoding="utf-8") == "# 报告\n\n内容"


def test_read_markdown_file_from_knowledge_workspace(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "报告.md"
    target.write_text("# 标题\n\n正文", encoding="utf-8")

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    response = client.get(
        "/knowledge-workspace/files/content",
        params={"relative_path": "报告.md"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["relative_path"] == "报告.md"
    assert body["content"].replace("\r\n", "\n") == "# 标题\n\n正文"
    assert body["truncated"] is False


def test_reject_non_text_file_from_knowledge_workspace(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "diagram.png"
    target.write_bytes(b"png")

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    response = client.get(
        "/knowledge-workspace/files/content",
        params={"relative_path": "diagram.png"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "only text and markdown files are supported"
