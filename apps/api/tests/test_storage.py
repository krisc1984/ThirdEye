import pytest

from app.services.storage import JsonStorage, StorageError


def test_save_and_load_json_by_namespace(tmp_path):
    storage = JsonStorage(tmp_path)

    path = storage.save_json("projects", "proj_1", {"id": "proj_1", "name": "Demo"})
    loaded = storage.load_json("projects", "proj_1")

    assert path.exists()
    assert loaded == {"id": "proj_1", "name": "Demo"}


def test_list_namespace_records(tmp_path):
    storage = JsonStorage(tmp_path)

    storage.save_json("projects", "proj_b", {"id": "proj_b"})
    storage.save_json("projects", "proj_a", {"id": "proj_a"})

    assert storage.list_json("projects") == [{"id": "proj_a"}, {"id": "proj_b"}]


def test_rejects_path_traversal_ids(tmp_path):
    storage = JsonStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save_json("projects", "../secret", {"id": "bad"})

    with pytest.raises(StorageError):
        storage.save_json("../outside", "proj_1", {"id": "bad"})


def test_creates_parent_directories_automatically(tmp_path):
    storage = JsonStorage(tmp_path / "data")

    path = storage.save_json("reviews", "review_1", {"id": "review_1"})

    assert path.exists()
    assert (tmp_path / "data" / "reviews").exists()


def test_playbook_artifact_storage(tmp_path):
    storage = JsonStorage(tmp_path)

    path = storage.save_playbook_artifact("pb_1", "playbook.skill.md", "# Skill")
    content = storage.load_playbook_artifact("pb_1", "playbook.skill.md")

    assert path.name == "playbook.skill.md"
    assert content == "# Skill"


def test_playbook_artifact_rejects_escape(tmp_path):
    storage = JsonStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save_playbook_artifact("pb_1", "../outside.md", "bad")

