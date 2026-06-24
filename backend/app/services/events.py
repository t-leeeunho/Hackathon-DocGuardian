"""Minimal in-process event bus for the WebSocket dashboard (README §8B WS /stream).

Governed writes publish small, typed event envelopes (type + ids + version/asOf);
the WebSocket endpoint forwards them and lets the frontend re-fetch full DTOs via
ACL-checked REST. Events are intentionally tiny and carry no restricted content.

This is deliberately simple (single process, best-effort). It is safe to publish
from FastAPI's sync threadpool: each subscriber records its event loop so cross-
thread delivery uses ``call_soon_threadsafe``.
"""

from __future__ import annotations

import asyncio
from typing import Any

_subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []


def subscribe() -> asyncio.Queue:
    """Register the current task as a subscriber. Call from an async context."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append((loop, queue))
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    global _subscribers
    _subscribers = [(loop, q) for (loop, q) in _subscribers if q is not queue]


def publish(event_type: str, **fields: Any) -> None:
    """Fan out a tiny event to every subscriber. Best-effort, never raises."""
    event = {"type": event_type, **fields}
    for loop, queue in list(_subscribers):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception:  # pragma: no cover - dead/closing subscriber
            unsubscribe(queue)
