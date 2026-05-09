from pathlib import Path

from app.services.secret_scanner import SecretScanner


def test_secret_scanner_detects_env_file_and_openai_key(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    secret_file = root / ".env"
    secret_file.write_text("OPENAI_API_KEY=sk-test", encoding="utf-8")

    findings = SecretScanner().scan_path(root, ".env")

    reasons = {finding.reason for finding in findings}
    assert "dotenv_file" in reasons
    assert "openai_api_key" in reasons
    assert "sk_token" in reasons
    assert all("sk-test" not in finding.redacted_summary for finding in findings)


def test_secret_scanner_detects_password_and_private_key(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file_path = root / "config.py"
    file_path.write_text(
        'password="hunter2"\n-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----',
        encoding="utf-8",
    )

    findings = SecretScanner().scan_path(root, "config.py")

    reasons = {finding.reason for finding in findings}
    assert "password_assignment" in reasons
    assert "private_key" in reasons
