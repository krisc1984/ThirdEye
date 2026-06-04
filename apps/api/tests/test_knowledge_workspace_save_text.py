from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.services.docx_document import render_docx_bytes


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


def test_save_and_read_docx_file_from_knowledge_workspace(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    save_response = client.post(
        "/knowledge-workspace/files/save-docx",
        json={
            "filename": "设计评审.docx",
            "content": "标题\n第一段内容\n第二段内容",
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["uploaded_files"] == ["设计评审.docx"]
    assert (workspace / "设计评审.docx").read_bytes().startswith(b"PK")

    read_response = client.get(
        "/knowledge-workspace/files/docx/content",
        params={"relative_path": "设计评审.docx"},
    )

    assert read_response.status_code == 200
    body = read_response.json()
    assert body["relative_path"] == "设计评审.docx"
    assert body["content_type"] == "docx"
    assert "标题" in body["content"]
    assert "第一段内容" in body["content"]
    assert body["truncated"] is False


def test_read_uploaded_docx_file_from_knowledge_workspace(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "上传文档.docx"
    target.write_bytes(render_docx_bytes("需求背景\n用户流程"))

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    response = client.get(
        "/knowledge-workspace/files/docx/content",
        params={"relative_path": "上传文档.docx"},
    )

    assert response.status_code == 200
    assert response.json()["content"].replace("\r\n", "\n") == "需求背景\n用户流程"


def test_save_docx_preserves_source_package_parts(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    source = workspace / "源文档.docx"
    source.write_bytes(render_docx_bytes("原始标题\n原始正文"))
    with ZipFile(source, "a", ZIP_DEFLATED) as archive:
        archive.writestr("word/media/image1.png", b"fake-image")
        archive.writestr("word/comments.xml", b"<w:comments/>")
        archive.writestr("customXml/item1.xml", b"<root>custom</root>")

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    save_response = client.post(
        "/knowledge-workspace/files/save-docx",
        json={
            "filename": "输出文档.docx",
            "content": "新标题\n新正文",
            "source_relative_path": "源文档.docx",
        },
    )

    assert save_response.status_code == 200
    output = workspace / "输出文档.docx"
    with ZipFile(output) as archive:
        assert archive.read("word/media/image1.png") == b"fake-image"
        assert archive.read("word/comments.xml") == b"<w:comments/>"
        assert archive.read("customXml/item1.xml") == b"<root>custom</root>"

    read_response = client.get(
        "/knowledge-workspace/files/docx/content",
        params={"relative_path": "输出文档.docx"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["content"].replace("\r\n", "\n") == "新标题\n新正文"


def test_save_docx_can_overwrite_source_package(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    source = workspace / "源文档.docx"
    source.write_bytes(render_docx_bytes("原始标题\n原始正文"))
    with ZipFile(source, "a", ZIP_DEFLATED) as archive:
        archive.writestr("word/media/image1.png", b"fake-image")

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    save_response = client.post(
        "/knowledge-workspace/files/save-docx",
        json={
            "filename": "源文档.docx",
            "content": "覆盖标题\n覆盖正文",
            "source_relative_path": "源文档.docx",
        },
    )

    assert save_response.status_code == 200
    assert not (workspace / ".源文档.docx.tmp").exists()
    with ZipFile(source) as archive:
        assert archive.read("word/media/image1.png") == b"fake-image"

    read_response = client.get(
        "/knowledge-workspace/files/docx/content",
        params={"relative_path": "源文档.docx"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["content"].replace("\r\n", "\n") == "覆盖标题\n覆盖正文"


def test_reject_non_docx_file_from_docx_reader(tmp_path):
    client = TestClient(app)
    workspace = tmp_path / "knowledge"
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "报告.md"
    target.write_text("# 标题", encoding="utf-8")

    client.put("/knowledge-workspace", json={"root_path": str(workspace)})
    response = client.get(
        "/knowledge-workspace/files/docx/content",
        params={"relative_path": "报告.md"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "only docx files are supported"
