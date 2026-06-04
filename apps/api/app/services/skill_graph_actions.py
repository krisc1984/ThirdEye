from __future__ import annotations

from collections.abc import Callable
from typing import Any


class GraphActionError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class TransientGraphActionError(GraphActionError):
    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


GraphActionHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
