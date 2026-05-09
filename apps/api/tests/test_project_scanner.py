from pathlib import Path

from app.services.project_scanner import ProjectScanner


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_scanner_respects_default_ignored_folders():
    summary = ProjectScanner().scan(FIXTURE)

    assert all("node_modules" not in item for item in summary.docs)
    assert all(".git" not in item for item in summary.docs)


def test_scanner_respects_gitignore():
    summary = ProjectScanner().scan(FIXTURE)

    assert "ignored.md" not in summary.docs
    assert "src/config.tmp" not in summary.config_files


def test_scanner_returns_language_counts():
    summary = ProjectScanner().scan(FIXTURE)

    assert summary.languages["python"] == 2
    assert summary.languages["markdown"] == 1


def test_scanner_returns_document_and_test_files():
    summary = ProjectScanner().scan(FIXTURE)

    assert summary.docs == ["README.md"]
    assert summary.tests == ["tests/test_app.py"]


def test_scanner_flags_sensitive_files_without_counting_as_scanned():
    summary = ProjectScanner().scan(FIXTURE)

    assert any("src/.env" in item for item in summary.sensitive_warnings)
    assert summary.skipped_files >= 1


def test_scanner_redacts_secret_like_content_in_warnings(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "config.py").write_text("OPENAI_API_KEY=sk-secret", encoding="utf-8")

    summary = ProjectScanner().scan(project)

    assert any("Value redacted" in item for item in summary.sensitive_warnings)
    assert all("sk-secret" not in item for item in summary.sensitive_warnings)


def test_scanner_skips_files_above_size_limit(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Demo", encoding="utf-8")
    (project / "large.py").write_text("x" * (513 * 1024), encoding="utf-8")

    summary = ProjectScanner().scan(project)

    assert summary.scanned_files == 1
    assert summary.skipped_files == 1


def test_scanner_skips_inaccessible_paths(tmp_path, monkeypatch):
    scanner = ProjectScanner()
    root = tmp_path / "project"
    root.mkdir()

    inaccessible = root / "venv" / "lib64"
    inaccessible.parent.mkdir(parents=True)

    original_is_file = Path.is_file

    def patched_is_file(self: Path):
        if self == inaccessible:
            raise OSError("inaccessible")
        return original_is_file(self)

    monkeypatch.setattr(Path, "is_file", patched_is_file)
    monkeypatch.setattr(Path, "rglob", lambda self, _pattern: [inaccessible] if self == root else [])

    summary = scanner.scan(root)

    assert summary.scanned_files == 0
    assert summary.skipped_files == 1
    assert any("could not be accessed" in item for item in summary.sensitive_warnings)
