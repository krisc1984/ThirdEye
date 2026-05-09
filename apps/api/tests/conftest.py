from pathlib import Path

import pytest

from app.core.config import settings


collect_ignore_glob = ["fixtures/**"]


@pytest.fixture(autouse=True)
def isolate_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", Path(data_dir))
    return data_dir
