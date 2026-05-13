from io import BytesIO
import zipfile

from fastapi.testclient import TestClient

from app.main import app


def _build_skill_zip(name: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            f"{name}/SKILL.md",
            "---\nname: sample-skill\ndescription: uploaded sample skill\n---\n\n# Sample Skill\n\nBody",
        )
    return buffer.getvalue()


def test_manage_skills_list_and_toggle_affects_public_skills():
    client = TestClient(app)

    listed = client.get("/skills/manage")
    assert listed.status_code == 200
    items = listed.json()
    assert isinstance(items, list)
    assert items

    target = items[0]["name"]
    toggled = client.post(f"/skills/manage/{target}/toggle", json={"enabled": False})
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False

    public_list = client.get("/skills")
    assert public_list.status_code == 200
    assert all(item["name"] != target for item in public_list.json())


def test_manage_skills_upload_detail_and_delete_uploaded_skill():
    client = TestClient(app)

    uploaded = client.post(
        "/skills/manage/upload",
        files={"file": ("demo-skill.zip", _build_skill_zip("demo-skill"), "application/zip")},
    )
    assert uploaded.status_code == 200
    installed = uploaded.json()["installed"]
    assert installed["name"] == "demo-skill"
    assert installed["enabled"] is True
    assert installed["source"] == "uploaded"

    detail = client.get("/skills/manage/demo-skill")
    assert detail.status_code == 200
    assert "Sample Skill" in detail.json()["content"]

    deleted = client.delete("/skills/manage/demo-skill")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
