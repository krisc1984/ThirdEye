from pathlib import Path
import shutil

import pytest

from app.core.config import settings


collect_ignore_glob = ["fixtures/**"]


@pytest.fixture(autouse=True)
def isolate_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sample_graph_root = Path(__file__).resolve().parents[3] / "data" / "skill-graph"
    if sample_graph_root.exists():
        shutil.copytree(sample_graph_root, data_dir / "skill-graph", dirs_exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", Path(data_dir))
    return data_dir
