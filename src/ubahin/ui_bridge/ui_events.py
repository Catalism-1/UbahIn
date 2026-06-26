from __future__ import annotations

from collections import defaultdict
from typing import Callable


class UiEventHub:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def on(self, event_name: str, callback: Callable[..., None]) -> None:
        self._listeners[event_name].append(callback)

    def emit(self, event_name: str, *args: object) -> None:
        for callback in tuple(self._listeners.get(event_name, [])):
            callback(*args)
