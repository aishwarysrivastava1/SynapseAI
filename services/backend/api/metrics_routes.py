from __future__ import annotations

import datetime
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from db.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from services.chatbot.queue import queue_manager
from services.chatbot.cost_control import DynamicCostTracker
from db.models import GlobalResourceCounter

router = APIRouter()

_METRICS_SECRET = os.getenv("METRICS_SECRET", "")

# Global counters — incremented by chatbot_routes
metric_cache_hits = 0
metric_guardrail_blocks = 0
metric_generator_partials = 0


def _require_metrics_token(x_metrics_token: str = Header(default="")):
    """Block unauthenticated access to internal metrics."""
    if not _METRICS_SECRET:
        raise HTTPException(status_code=503, detail="Metrics endpoint not configured")
    if not secrets.compare_digest(x_metrics_token, _METRICS_SECRET):
        raise HTTPException(status_code=401, detail="Invalid metrics token")


@router.get("", dependencies=[Depends(_require_metrics_token)])
async def export_metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus-compatible scrape endpoint.
    Requires X-Metrics-Token header matching METRICS_SECRET env var.
    """
    payload = []

    def add_metric(name: str, val: float, help_text: str, metric_type: str = "gauge"):
        payload.append(f"# HELP {name} {help_text}")
        payload.append(f"# TYPE {name} {metric_type}")
        payload.append(f"{name} {val}")

    add_metric(
        "chatbot_active_requests",
        queue_manager.active_slots,
        "Connections currently processing LLM or DB blocks",
    )

    add_metric(
        "chatbot_queue_size",
        queue_manager.queued_slots,
        "Requests pending backpressure evaluation",
    )

    is_blocked = await DynamicCostTracker.is_cost_blocked(db)
    add_metric(
        "chatbot_circuit_breaker_active",
        1.0 if is_blocked else 0.0,
        "Boolean mapping if global TPM cost blocker is actively triggered",
    )

    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(second=0, microsecond=0, tzinfo=None)
    stmt = select(GlobalResourceCounter.current_value).where(
        GlobalResourceCounter.resource_key == "gemini_tpm",
        GlobalResourceCounter.timestamp_minute == now,
    )
    res = await db.execute(stmt)
    tpm = res.scalar() or 0

    add_metric(
        "chatbot_tpm_1min_rolling",
        tpm,
        "Estimated tokens consumed within trailing 1-minute window (DB-backed)",
    )

    add_metric(
        "chatbot_cache_hits_total",
        metric_cache_hits,
        "Total cache hits avoiding LLM API completely",
        "counter",
    )

    add_metric(
        "chatbot_total_guardrail_blocks",
        metric_guardrail_blocks,
        "Total requests halted natively by heuristics pipeline",
        "counter",
    )

    add_metric(
        "chatbot_partial_generator_interrupts",
        metric_generator_partials,
        "Total cancelled client generators resulting in partial database commits",
        "counter",
    )

    return PlainTextResponse("\n".join(payload) + "\n", media_type="text/plain")
