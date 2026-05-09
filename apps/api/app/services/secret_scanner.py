from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SecretScanFinding:
    path: str
    reason: str
    redacted_summary: str


class SecretScanner:
    SECRET_PATTERNS = {
        "openai_api_key": re.compile(r"OPENAI_API_KEY\s*=", re.IGNORECASE),
        "sk_token": re.compile(r"\bsk-[A-Za-z0-9_-]+\b"),
        "password_assignment": re.compile(r"password\s*=", re.IGNORECASE),
        "private_key": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    }

    def scan_path(self, root: Path, relative_path: str) -> list[SecretScanFinding]:
        path = root / relative_path
        lower_name = path.name.lower()
        findings: list[SecretScanFinding] = []

        if lower_name.startswith(".env"):
            findings.append(
                SecretScanFinding(
                    path=relative_path,
                    reason="dotenv_file",
                    redacted_summary="Dotenv file may contain secrets. Content is intentionally not ingested.",
                )
            )

        try:
            content = path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError, OSError):
            return findings

        for reason, pattern in self.SECRET_PATTERNS.items():
            if not pattern.search(content):
                continue
            findings.append(
                SecretScanFinding(
                    path=relative_path,
                    reason=reason,
                    redacted_summary=self._redacted_summary(reason),
                )
            )

        deduped: dict[tuple[str, str], SecretScanFinding] = {}
        for finding in findings:
            deduped[(finding.path, finding.reason)] = finding
        return list(deduped.values())

    def _redacted_summary(self, reason: str) -> str:
        messages = {
            "openai_api_key": "Detected an OpenAI API key assignment. Value redacted.",
            "sk_token": "Detected an API token-like secret. Value redacted.",
            "password_assignment": "Detected a password-style assignment. Value redacted.",
            "private_key": "Detected a private key block. Content redacted.",
            "dotenv_file": "Dotenv file may contain secrets. Content is intentionally not ingested.",
        }
        return messages[reason]
