from __future__ import annotations

import logging
import datetime
import asyncio
from typing import Any

from django.conf import settings

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@sync_to_async
def _flush_to_db(work_batch: list[dict]) -> None:
    from apps.accounts.models import VolunteerProfile
    for item in work_batch:
        VolunteerProfile.objects.filter(user_id=item["volunteer_id"]).update(
            lat=item["lat"],
            lng=item["lng"],
            share_location=item["share_location"],
            last_active_at=item["timestamp"],
        )


@sync_to_async
def _get_profile(volunteer_id: str):
    from apps.accounts.models import VolunteerProfile
    return VolunteerProfile.objects.filter(user_id=volunteer_id).values(
        "lat", "lng", "share_location", "last_active_at"
    ).first()


class LiveLocationCache:
    """
    Location manager with write buffering and batch Django ORM updates.
    Replaces SQLAlchemy AsyncSession + PostgreSQL dialect insert.
    """

    def __init__(self) -> None:
        self._enabled = True
        self._ttl_seconds = getattr(settings, "REDIS_LOCATION_TTL_SECONDS", 120)
        self._buffer: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._flush_interval = 1.5

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def startup(self) -> None:
        self._enabled = True
        logger.info("Live location system: Batching Mode Active (Django ORM)")

    async def shutdown(self) -> None:
        self._enabled = False
        await self.flush()

    async def set_location(
        self,
        volunteer_id: str,
        ngo_id: str | None,
        lat: float | None,
        lng: float | None,
        share_location: bool,
    ) -> None:
        async with self._lock:
            self._buffer[volunteer_id] = {
                "volunteer_id": volunteer_id,
                "lat": lat,
                "lng": lng,
                "share_location": share_location,
                "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None),
            }
            if not self._flush_task or self._flush_task.done():
                try:
                    self._flush_task = asyncio.ensure_future(self._scheduled_flush())
                except RuntimeError:
                    pass  # no running event loop; next async call will trigger flush

    async def update(self, volunteer_id: str, lat: float, lng: float, share_location: bool) -> None:
        await self.set_location(volunteer_id, None, lat, lng, share_location)

    async def _scheduled_flush(self) -> None:
        await asyncio.sleep(self._flush_interval)
        await self.flush()

    async def flush(self) -> None:
        async with self._lock:
            if not self._buffer:
                return
            work_batch = list(self._buffer.values())
            self._buffer = {}

        if not work_batch:
            return

        try:
            await _flush_to_db(work_batch)
            logger.debug("Flushed %s location updates to DB", len(work_batch))
        except Exception as e:
            logger.error("Failed to flush location batch: %s", e)

    async def get_location(self, volunteer_id: str) -> dict[str, Any] | None:
        async with self._lock:
            if volunteer_id in self._buffer:
                return self._buffer[volunteer_id]

        try:
            profile = await _get_profile(volunteer_id)
            if not profile or profile["lat"] is None or profile["lng"] is None:
                return None
            now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
            if profile.get("last_active_at"):
                delta = (now - profile["last_active_at"]).total_seconds()
                if delta > self._ttl_seconds:
                    return None
            return {"lat": profile["lat"], "lng": profile["lng"],
                    "share_location": profile.get("share_location", False)}
        except Exception as e:
            logger.error("get_location failed: %s", e)
            return None


live_location_cache = LiveLocationCache()
