from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RealtimeEventBus:
    """Channel-name-based event bus for Django Channels.
    
    Stores channel_name strings (not WebSocket objects).
    Uses Redis channel layer to push messages to connected consumers.
    """

    def __init__(self) -> None:
        self._ngo_channels: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, ngo_id: str, channel_name: str) -> None:
        async with self._lock:
            self._ngo_channels[ngo_id].add(channel_name)

    async def disconnect(self, ngo_id: str, channel_name: str) -> None:
        async with self._lock:
            bucket = self._ngo_channels.get(ngo_id)
            if bucket:
                bucket.discard(channel_name)
                if not bucket:
                    self._ngo_channels.pop(ngo_id, None)

    async def publish(self, ngo_id: str | None, event: str, payload: dict) -> None:
        scope = ngo_id or "global"
        async with self._lock:
            channels = list(self._ngo_channels.get(scope, set()))
        if not channels:
            return

        envelope = {
            "event": event,
            "payload": payload,
            "timestamp": dt.datetime.now(tz=dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        }

        try:
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
        except Exception:
            logger.debug("Channel layer unavailable — skipping realtime publish")
            return

        stale: list[str] = []
        for ch in channels:
            try:
                await channel_layer.send(ch, {
                    "type": "realtime.message",
                    "message": envelope,
                })
            except Exception:
                stale.append(ch)

        if stale:
            async with self._lock:
                bucket = self._ngo_channels.get(scope, set())
                for ch in stale:
                    bucket.discard(ch)
                if not bucket:
                    self._ngo_channels.pop(scope, None)
            logger.debug("Cleaned %s stale channel(s) for ngo scope %s", len(stale), scope)

    def stats(self) -> dict:
        return {
            "active_ngo_scopes": len(self._ngo_channels),
            "active_connections": sum(len(v) for v in self._ngo_channels.values()),
        }


realtime_bus = RealtimeEventBus()
