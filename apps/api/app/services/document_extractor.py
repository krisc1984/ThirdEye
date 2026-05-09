from __future__ import annotations

from pathlib import Path


class DocumentExtractor:
    def extract_chunks(self, root_path: Path, relative_path: str, max_chars: int = 1200) -> list[dict[str, str]]:
        path = root_path / relative_path
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks: list[dict[str, str]] = []
        current_heading = "Document"
        current_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("#"):
                self._append_chunk(chunks, current_heading, current_lines, max_chars)
                current_heading = line.lstrip("#").strip() or "Document"
                current_lines = []
            else:
                current_lines.append(line)

        self._append_chunk(chunks, current_heading, current_lines, max_chars)
        if not chunks and text.strip():
            chunks.append({"symbol": "Document", "summary": text.strip()[:max_chars]})
        return chunks

    def _append_chunk(
        self,
        chunks: list[dict[str, str]],
        heading: str,
        lines: list[str],
        max_chars: int,
    ) -> None:
        content = "\n".join(lines).strip()
        if not content:
            return
        chunks.append({"symbol": heading, "summary": content[:max_chars]})

