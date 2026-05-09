from __future__ import annotations

import asyncio
from threading import Lock


class ReviewSessionAlreadyRunningError(RuntimeError):
    pass


class ReviewSessionRunRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Task[object]]] = {}
        self._lock = Lock()

    def start(self, session_id: str, task: asyncio.Task[object]) -> None:
        with self._lock:
            existing = self._tasks.get(session_id)
            if existing is not None and not existing[1].done():
                raise ReviewSessionAlreadyRunningError(session_id)
            self._tasks[session_id] = (asyncio.get_running_loop(), task)

    def finish(self, session_id: str, task: asyncio.Task[object]) -> None:
        with self._lock:
            current = self._tasks.get(session_id)
            if current is not None and current[1] is task:
                self._tasks.pop(session_id, None)

    def cancel(self, session_id: str) -> bool:
        with self._lock:
            running = self._tasks.get(session_id)
            if running is None or running[1].done():
                return False
            loop, task = running
            loop.call_soon_threadsafe(task.cancel)
            return True

    def is_running(self, session_id: str) -> bool:
        with self._lock:
            running = self._tasks.get(session_id)
            return running is not None and not running[1].done()


review_session_runs = ReviewSessionRunRegistry()
