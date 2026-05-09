from pathlib import Path

from app.services.evidence_builder import EvidenceBuilder
from app.services.project_scanner import ProjectScanner


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


def test_builds_evidence_from_sample_project():
    scan = ProjectScanner().scan(FIXTURE)
    evidence = EvidenceBuilder().build("proj_sample", scan)

    assert evidence
    assert {item.source_type for item in evidence} >= {"doc", "code", "test"}


def test_readme_becomes_doc_evidence():
    scan = ProjectScanner().scan(FIXTURE)
    evidence = EvidenceBuilder().build("proj_sample", scan)

    readme = [item for item in evidence if item.path == "README.md"]
    assert readme
    assert readme[0].source_type == "doc"
    assert "workflow code" in readme[0].summary


def test_source_files_become_code_evidence_with_symbols():
    scan = ProjectScanner().scan(FIXTURE)
    evidence = EvidenceBuilder().build("proj_sample", scan)

    app = next(item for item in evidence if item.path == "src/app.py")
    assert app.source_type == "code"
    assert app.symbol == "run_app"
    assert "Defines symbols" in app.summary


def test_tests_become_test_evidence():
    scan = ProjectScanner().scan(FIXTURE)
    evidence = EvidenceBuilder().build("proj_sample", scan)

    test_item = next(item for item in evidence if item.path == "tests/test_app.py")
    assert test_item.source_type == "test"
    assert "regression coverage" in test_item.summary


def test_evidence_ids_are_stable():
    scan = ProjectScanner().scan(FIXTURE)
    first = EvidenceBuilder().build("proj_sample", scan)
    second = EvidenceBuilder().build("proj_sample", scan)

    assert [item.id for item in first] == [item.id for item in second]


def test_secret_like_source_is_not_ingested_verbatim(tmp_path):
    project = tmp_path / "project"
    src = project / "src"
    src.mkdir(parents=True)
    (project / "README.md").write_text("# Demo", encoding="utf-8")
    (src / "app.py").write_text('OPENAI_API_KEY="sk-secret"', encoding="utf-8")

    scan = ProjectScanner().scan(project)
    evidence = EvidenceBuilder().build("proj_secret", scan)

    secret_item = next(item for item in evidence if item.path == "src/app.py")
    assert "redacted" in secret_item.summary.lower()
    assert "sk-secret" not in secret_item.summary


def test_builder_skips_inaccessible_code_paths(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Demo", encoding="utf-8")

    inaccessible = project / "venv" / "lib64"
    inaccessible.parent.mkdir(parents=True)

    original_is_file = Path.is_file
    original_rglob = Path.rglob

    def patched_is_file(self: Path):
        if self == inaccessible:
            raise OSError("inaccessible")
        return original_is_file(self)

    def patched_rglob(self: Path, pattern: str):
        if self == project:
            yield inaccessible
            yield from original_rglob(self, pattern)
            return
        yield from original_rglob(self, pattern)

    monkeypatch.setattr(Path, "is_file", patched_is_file)
    monkeypatch.setattr(Path, "rglob", patched_rglob)

    scan = ProjectScanner().scan(project)
    evidence = EvidenceBuilder().build("proj_sample", scan)

    assert isinstance(evidence, list)
