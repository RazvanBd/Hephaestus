from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, Dict, List

from fastapi import WebSocket

EventHandler = Callable[[Dict], Awaitable[None]]


class AsyncEventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        self._sockets: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._sockets.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._sockets:
                self._sockets.remove(websocket)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Dict) -> None:
        message = {"event": event_type, "payload": payload}
        for handler in self._subscribers[event_type]:
            await handler(payload)

        async with self._lock:
            for socket in list(self._sockets):
                try:
                    await socket.send_text(json.dumps(message))
                except Exception:
                    self._sockets.remove(socket)
