import json
from datetime import datetime

from app.services.audit_log import AuditLogger


def test_audit_logger_writes_jsonl_and_redacts_keys(tmp_path):
    logger = AuditLogger(tmp_path)

    path = logger.log_event(
        {
            "workflow": "playbook_distillation",
            "provider": {"api_key": "secret"},
            "proposal_content": "A" * 300,
        },
        at=datetime(2026, 5, 7, 12, 0, 0),
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["provider"]["api_key"] == "********"
    assert payload["proposal_content"].endswith("...")
    assert len(payload["proposal_content"]) < 260


def test_audit_logger_keeps_file_paths_not_file_content(tmp_path):
    logger = AuditLogger(tmp_path)

    path = logger.log_event(
        {
            "artifact_paths": ["data/playbooks/pb_sample_v1/playbook.skill.md"],
            "file_content": "sensitive body",
        },
        at=datetime(2026, 5, 7, 12, 0, 0),
    )

    payload = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["artifact_paths"] == ["data/playbooks/pb_sample_v1/playbook.skill.md"]
    assert "file_content" not in payload


def test_audit_logger_redacts_secret_like_string_values(tmp_path):
    logger = AuditLogger(tmp_path)

    path = logger.log_event(
        {"note": "OPENAI_API_KEY=sk-secret"},
        at=datetime(2026, 5, 7, 12, 0, 0),
    )

    payload = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["note"] == "********"
