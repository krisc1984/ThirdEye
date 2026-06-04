from __future__ import annotations

import asyncio
from datetime import datetime
from collections import defaultdict
from threading import Lock
from typing import Any

from app.schemas.skill_graph import GraphRun
from app.services.storage import GRAPH_RUNS_NAMESPACE, JsonStorage

GRAPH_RUN_EVENT_NAMESPACE = "skill-graph/run-events"


class SkillGraphRunEventService:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def append_run_event(self, run: GraphRun, *, event_type: str) -> dict[str, Any]:
        events = self.list_run_events(run.id)
        self.storage.save_json(GRAPH_RUNS_NAMESPACE, run.id, run.model_dump(mode="json"))
        event = {
            "run_id": run.id,
            "sequence": len(events) + 1,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "status": run.status,
                "current_node_id": run.current_node_id,
                "node_state": run.node_states[-1].model_dump(mode="json") if run.node_states else None,
                "approvals": [item.model_dump(mode="json") for item in run.approvals],
            },
        }
        self.storage.save_json(GRAPH_RUN_EVENT_NAMESPACE, run.id, {"events": [*events, event]})
        skill_graph_run_events.publish(run.id, event)
        return event

    def list_run_events(self, run_id: str) -> list[dict[str, Any]]:
        try:
            payload = self.storage.load_json(GRAPH_RUN_EVENT_NAMESPACE, run_id)
        except FileNotFoundError:
            return []
        events = payload.get("events", [])
        return [item for item in events if isinstance(item, dict)]

    def replay_run_snapshot(self, run_id: str) -> dict[str, Any]:
        run_payload = self.storage.load_json(GRAPH_RUNS_NAMESPACE, run_id)
        return {
            "run_id": run_id,
            "sequence": 0,
            "event_type": "snapshot",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": run_payload,
        }


class SkillGraphRunEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._lock = Lock()

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            queues = list(self._subscribers.get(run_id, []))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue

    def subscribe(self, run_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        with self._lock:
            self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(run_id)
            if not subscribers:
                return
            self._subscribers[run_id] = [item for item in subscribers if item is not queue]
            if not self._subscribers[run_id]:
                self._subscribers.pop(run_id, None)


skill_graph_run_events = SkillGraphRunEventBus()
