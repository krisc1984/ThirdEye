from __future__ import annotations

import re
from pathlib import Path

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
}


class CodeExtractor:
    def extract(self, root_path: Path, relative_path: str) -> dict[str, object]:
        path = root_path / relative_path
        text = path.read_text(encoding="utf-8", errors="ignore")
        language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")
        symbols = self._extract_symbols(text, language)
        imports = self._extract_imports(text, language)
        summary_parts = []
        if symbols:
            summary_parts.append(f"Defines symbols: {', '.join(symbols[:8])}.")
        if imports:
            summary_parts.append(f"Imports: {', '.join(imports[:8])}.")
        if not summary_parts:
            summary_parts.append("Source file with no top-level symbols detected.")

        return {
            "language": language,
            "symbols": symbols,
            "imports": imports,
            "summary": " ".join(summary_parts),
        }

    def _extract_symbols(self, text: str, language: str) -> list[str]:
        patterns = {
            "python": r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
            "typescript": r"^(?:export\s+)?(?:function|class|interface|type|const)\s+([A-Za-z_][A-Za-z0-9_]*)",
            "javascript": r"^(?:export\s+)?(?:function|class|const)\s+([A-Za-z_][A-Za-z0-9_]*)",
            "go": r"^func\s+([A-Za-z_][A-Za-z0-9_]*)",
        }
        pattern = patterns.get(language)
        if not pattern:
            return []
        return re.findall(pattern, text, flags=re.MULTILINE)

    def _extract_imports(self, text: str, language: str) -> list[str]:
        if language == "python":
            imports = re.findall(r"^(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))", text, flags=re.MULTILINE)
            return [left or right for left, right in imports]
        if language in {"typescript", "javascript"}:
            return re.findall(r"from\s+['\"]([^'\"]+)['\"]", text)
        if language == "go":
            return re.findall(r"import\s+\"([^\"]+)\"", text)
        return []

