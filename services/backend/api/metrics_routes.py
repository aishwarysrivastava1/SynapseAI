import time
import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from db.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from services.chatbot.queue import queue_manager
from services.chatbot.cost_control import DynamicCostTracker
from db.models import GlobalResourceCounter

router = APIRouter()

# Global variables counting metrics natively without heavy external integrations
metric_cache_hits = 0
metric_guardrail_blocks = 0
metric_generator_partials = 0

@router.get("")
async def export_metrics(db: AsyncSession = Depends(get_db)):
    """
    Exposes structural state conforming to Prometheus native scraping payload.
    Network boundaries externally protect this route intrinsically.
    """
    
    payload = []
    
    # Header format helpers
    def add_metric(name: str, val: float, help_text: str, metric_type: str = "gauge"):
        payload.append(f"# HELP {name} {help_text}")
        payload.append(f"# TYPE {name} {metric_type}")
        payload.append(f"{name} {val}")
        
    add_metric(
        "chatbot_active_requests", 
        queue_manager.active_slots, 
        "Connections currently processing LLM or DB blocks"
    )
    
    add_metric(
        "chatbot_queue_size", 
        queue_manager.queued_slots, 
        "Requests pending backpressure evaluation"
    )
    
    is_blocked = await DynamicCostTracker.is_cost_blocked(db)
    add_metric(
        "chatbot_circuit_breaker_active", 
        1.0 if is_blocked else 0.0, 
        "Boolean mapping if global TPM cost blocker is actively triggered"
    )
    
    # Fetch latest minute TPM from DB
    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    stmt = select(GlobalResourceCounter.current_value).where(
        GlobalResourceCounter.resource_key == "gemini_tpm",
        GlobalResourceCounter.timestamp_minute == now
    )
    res = await db.execute(stmt)
    tpm = res.scalar() or 0

    add_metric(
        "chatbot_tpm_1min_rolling", 
        tpm, 
        "Estimated tokens consumed within trailing 1-minute window (DB-backed)"
    )
    
    add_metric(
        "chatbot_cache_hits_total", 
        metric_cache_hits, 
        "Total cache hits avoiding LLM API completely",
        "counter"
    )

    add_metric(
        "chatbot_total_guardrail_blocks", 
        metric_guardrail_blocks, 
        "Total requests halted natively by heuristics pipeline",
        "counter"
    )
    
    add_metric(
        "chatbot_partial_generator_interrupts", 
        metric_generator_partials, 
        "Total cancelled client generators resulting in partial database commits",
        "counter"
    )
    
    return PlainTextResponse("\n".join(payload) + "\n", media_type="text/plain")
