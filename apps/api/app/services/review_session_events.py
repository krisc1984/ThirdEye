from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any


class ReviewSessionEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._sequences: dict[str, int] = defaultdict(int)
        self._lock = Lock()

    def publish(self, session_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._sequences[session_id] += 1
            sequence = self._sequences[session_id]
            queues = list(self._subscribers.get(session_id, []))
        event = {
            "session_id": session_id,
            "sequence": sequence,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue
        return event

    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        with self._lock:
            self._subscribers[session_id].append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(session_id)
            if not subscribers:
                return
            self._subscribers[session_id] = [item for item in subscribers if item is not queue]
            if not self._subscribers[session_id]:
                self._subscribers.pop(session_id, None)


def encode_sse_event(event: dict[str, Any]) -> str:
    return f"event: {event['event_type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


review_session_events = ReviewSessionEventBus()
