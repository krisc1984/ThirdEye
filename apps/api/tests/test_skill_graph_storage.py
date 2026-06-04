import pytest

from app.services.storage import (
    GRAPH_ASSETS_NAMESPACE,
    GRAPH_CAPABILITIES_NAMESPACE,
    GRAPH_COMPOSITES_NAMESPACE,
    GRAPH_PLAYBOOKS_NAMESPACE,
    GRAPH_RUNS_NAMESPACE,
    JsonStorage,
    StorageError,
)


def test_save_and_load_graph_definition_by_namespace(tmp_path):
    storage = JsonStorage(tmp_path)
    payload = {"id": "cap_fetch_page", "name": "Fetch Page"}

    path = storage.save_json(GRAPH_CAPABILITIES_NAMESPACE, "cap_fetch_page", payload)
    loaded = storage.load_json(GRAPH_CAPABILITIES_NAMESPACE, "cap_fetch_page")

    assert path.exists()
    assert loaded == payload


def test_list_graph_records(tmp_path):
    storage = JsonStorage(tmp_path)

    storage.save_json(GRAPH_COMPOSITES_NAMESPACE, "comp_z", {"id": "comp_z"})
    storage.save_json(GRAPH_COMPOSITES_NAMESPACE, "comp_a", {"id": "comp_a"})

    assert storage.list_json(GRAPH_COMPOSITES_NAMESPACE) == [{"id": "comp_a"}, {"id": "comp_z"}]


def test_save_and_load_nested_run_snapshot(tmp_path):
    storage = JsonStorage(tmp_path)
    payload = {"id": "run_1", "status": "running"}

    path = storage.save_graph_run_snapshot("run_1", "snapshots/step_01", payload)
    loaded = storage.load_graph_run_snapshot("run_1", "snapshots/step_01")

    assert path.exists()
    assert path.parent.name == "snapshots"
    assert loaded == payload


def test_rejects_graph_path_traversal(tmp_path):
    storage = JsonStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save_json(GRAPH_PLAYBOOKS_NAMESPACE, "../graph_bad", {"id": "graph_bad"})

    with pytest.raises(StorageError):
        storage.save_graph_run_snapshot("run_1", "../outside", {"id": "run_1"})


def test_graph_namespaces_match_storage_layout():
    assert GRAPH_CAPABILITIES_NAMESPACE == "skill-graph/capabilities"
    assert GRAPH_COMPOSITES_NAMESPACE == "skill-graph/composites"
    assert GRAPH_PLAYBOOKS_NAMESPACE == "skill-graph/graph-playbooks"
    assert GRAPH_RUNS_NAMESPACE == "skill-graph/runs"
    assert GRAPH_ASSETS_NAMESPACE == "skill-graph/assets"
