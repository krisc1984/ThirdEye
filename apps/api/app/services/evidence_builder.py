from __future__ import annotations

import hashlib
from pathlib import Path

from app.schemas.playbook import EvidenceItem
from app.schemas.project import ProjectScanSummary
from app.services.code_extractor import CodeExtractor
from app.services.document_extractor import DocumentExtractor
from app.services.secret_scanner import SecretScanner


class EvidenceBuilder:
    def __init__(self) -> None:
        self.document_extractor = DocumentExtractor()
        self.code_extractor = CodeExtractor()
        self.secret_scanner = SecretScanner()

    def build(self, project_id: str, scan: ProjectScanSummary) -> list[EvidenceItem]:
        root = Path(scan.root_path)
        evidence: list[EvidenceItem] = []

        for doc_path in scan.docs:
            for chunk in self.document_extractor.extract_chunks(root, doc_path):
                evidence.append(
                    self._item(
                        project_id=project_id,
                        source_type="doc",
                        path=doc_path,
                        symbol=chunk["symbol"],
                        summary=chunk["summary"],
                        metadata={"kind": "document"},
                    )
                )

        for test_path in scan.tests:
            evidence.append(
                self._item(
                    project_id=project_id,
                    source_type="test",
                    path=test_path,
                    symbol=None,
                    summary="Test file indicates expected project behavior and regression coverage.",
                    metadata={"kind": "test"},
                )
            )

        for config_path in scan.config_files:
            secret_findings = self.secret_scanner.scan_path(root, config_path)
            summary = "Configuration file contributes project tooling or runtime constraints."
            if secret_findings:
                summary = "Configuration file may contain sensitive runtime settings. Content was not ingested verbatim."
            evidence.append(
                self._item(
                    project_id=project_id,
                    source_type="config",
                    path=config_path,
                    symbol=None,
                    summary=summary,
                    metadata={"kind": "config"},
                )
            )

        known_paths = set(scan.docs) | set(scan.tests) | set(scan.config_files)
        for path in self._iter_code_files(root):
            relative = path.relative_to(root).as_posix()
            if relative in known_paths:
                continue
            secret_findings = self.secret_scanner.scan_path(root, relative)
            if secret_findings:
                evidence.extend(
                    self._secret_findings_as_evidence(project_id, secret_findings)
                )
                continue
            extracted = self.code_extractor.extract(root, relative)
            evidence.append(
                self._item(
                    project_id=project_id,
                    source_type="code",
                    path=relative,
                    symbol=", ".join(extracted["symbols"]) or None,
                    summary=str(extracted["summary"]),
                    metadata={"language": str(extracted["language"])},
                )
            )

        return sorted(evidence, key=lambda item: item.id)

    def _iter_code_files(self, root: Path) -> list[Path]:
        suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".go"}
        files: list[Path] = []
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            if path.suffix.lower() not in suffixes:
                continue
            if "node_modules" in path.parts or ".git" in path.parts:
                continue
            files.append(path)
        return files

    def _item(
        self,
        project_id: str,
        source_type: str,
        path: str,
        symbol: str | None,
        summary: str,
        metadata: dict[str, str],
        ) -> EvidenceItem:
        evidence_id = self._stable_id(project_id, path, symbol or source_type)
        return EvidenceItem(
            id=evidence_id,
            project_id=project_id,
            source_type=source_type,  # type: ignore[arg-type]
            path=path,
            symbol=symbol,
            summary=summary,
            evidence_level="confirmed",
            metadata=metadata,
        )

    def _secret_findings_as_evidence(
        self,
        project_id: str,
        findings,
    ) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        for finding in findings:
            evidence.append(
                self._item(
                    project_id=project_id,
                    source_type="config",
                    path=finding.path,
                    symbol=None,
                    summary=finding.redacted_summary,
                    metadata={"kind": "secret_warning"},
                )
            )
        return evidence

    def _stable_id(self, project_id: str, path: str, symbol: str) -> str:
        digest = hashlib.sha1(f"{project_id}:{path}:{symbol}".encode("utf-8")).hexdigest()[:12]
        return f"ev_{digest}"
