from __future__ import annotations

import json
from dataclasses import dataclass

from app.schemas.playbook import EvidenceItem, PlaybookMetadata, PlaybookRule
from app.services.storage import JsonStorage


@dataclass(frozen=True)
class LoadedPlaybook:
    metadata: PlaybookMetadata
    skill_markdown: str
    project_summary: str
    rules: list[PlaybookRule]
    evidence: list[EvidenceItem]


class PlaybookLoader:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def load(self, playbook_id: str) -> LoadedPlaybook:
        metadata = PlaybookMetadata.model_validate_json(
            self.storage.load_playbook_artifact(playbook_id, "metadata.json")
        )
        rules = [
            PlaybookRule.model_validate(item)
            for item in json.loads(self.storage.load_playbook_artifact(playbook_id, "rules.json"))
        ]
        evidence = [
            EvidenceItem.model_validate(json.loads(line))
            for line in self.storage.load_playbook_artifact(playbook_id, "evidence.jsonl").splitlines()
            if line.strip()
        ]
        return LoadedPlaybook(
            metadata=metadata,
            skill_markdown=self.storage.load_playbook_artifact(playbook_id, "playbook.skill.md"),
            project_summary=self.storage.load_playbook_artifact(playbook_id, "project-summary.md"),
            rules=rules,
            evidence=evidence,
        )
