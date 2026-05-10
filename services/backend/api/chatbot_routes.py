"""
Chatbot SSE streaming route.

Pipeline (in order):
  auth → queue → guardrails → cost_blocked? → user_budget? → semantic_cache?
  → live_context_build → token_optimizer → memory → LLM stream
  → output_guardrails → cost_record → session_persist → cache_store
"""
from __future__ import annotations

import json
import logging
import asyncio
import re
import uuid

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from middleware.rbac import get_current_user_or_none, CurrentUser
from services.chatbot.observability import Tracer, request_id_var
from services.chatbot.queue import queue_manager
from services.chatbot.cost_control import DynamicCostTracker
from services.chatbot.guardrails import GuardrailsPipeline
from services.chatbot.cache import SemanticCache
from services.chatbot.memory import HybridMemory
from services.chatbot.llm import LLMOrchestrator
from services.chatbot.sessionCache import SessionCache
from services.chatbot.optimizer import TokenOptimizer
from services.chatbot.prompts import build_system_prompt
import api.metrics_routes as metrics

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level semantic cache instance (stateless, safe to share)
_semantic_cache = SemanticCache()


# ── Live context helpers (Django ORM, sync_to_async) ─────────────────────────

@sync_to_async
def _fetch_ngo_context(ngo_id: str) -> dict:
    """Pull real-time NGO stats from PostgreSQL for system prompt injection."""
    try:
        from apps.ngo.models import Task, Assignment, Resource
        from apps.accounts.models import VolunteerProfile

        open_tasks       = Task.objects.filter(ngo_id=ngo_id, status="open").count()
        in_progress      = Task.objects.filter(ngo_id=ngo_id, status="in_progress").count()
        completed_today  = Task.objects.filter(
            ngo_id=ngo_id, status="completed"
        ).order_by("-updated_at")[:5].count()
        active_vols      = VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active").count()
        pending_assigns  = Assignment.objects.filter(ngo_id=ngo_id, status="assigned").count()

        return {
            "open_tasks":      open_tasks,
            "in_progress":     in_progress,
            "completed_today": completed_today,
            "active_vols":     active_vols,
            "pending_assigns": pending_assigns,
        }
    except Exception as exc:
        logger.warning("Could not fetch NGO context: %s", exc)
        return {}


def _format_live_context(ctx: dict, role: str, page: str) -> str:
    if not ctx:
        return ""
    lines = [
        f"User Role: {role} | Current Page: {page}",
        f"Open Tasks: {ctx.get('open_tasks', '?')} | In Progress: {ctx.get('in_progress', '?')}",
        f"Active Volunteers: {ctx.get('active_vols', '?')} | Pending Assignments: {ctx.get('pending_assigns', '?')}",
    ]
    return "\n".join(lines)


# ── Request schema ────────────────────────────────────────────────────────────

class ChatMessagePayload(BaseModel):
    message:       str
    imageBase64:   str | None = None
    imageMimeType: str | None = None
    context:       dict = {}


# ── Main route ────────────────────────────────────────────────────────────────

@router.post("")
async def chat_stream(
    req:     ChatMessagePayload,
    request: Request,
    user:    CurrentUser | None = Depends(get_current_user_or_none),
):
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)

    consent    = req.context.get("consent", False)
    role       = req.context.get("role", "visitor")
    page       = req.context.get("page", "/")
    ngo_id     = user.ngo_id if user else None
    is_guest   = user is None
    identifier = (
        user.user_id
        if user
        else getattr(request.state, "guest_id", None) or "anonymous_guest"
    )

    with Tracer(name="chat_request", user_id=identifier) as trace:

        # ── Session setup ─────────────────────────────────────────────────────
        try:
            if consent:
                session = await SessionCache.get_or_create_session(identifier, is_guest)
                session_id = session.id
            else:
                session_id = f"ephemeral_{identifier}"
        except Exception as exc:
            logger.error("Session creation failed, using ephemeral: %s", exc)
            session_id = f"ephemeral_{identifier}"
            consent    = False
        trace.session_id = session_id

        # ── Backpressure queue ────────────────────────────────────────────────
        try:
            await queue_manager.acquire(identifier, session_id)
        except ValueError:
            trace.add_event("rejected", "queue_full")
            return StreamingResponse(
                iter([f"data: {json.dumps({'error': 'Service is busy. Please try again shortly.'})}\n\n"]),
                media_type="text/event-stream",
            )

        async def event_generator():
            try:
                # 1. Guardrails ────────────────────────────────────────────────
                with Tracer(name="guardrails", session_id=session_id) as grd:
                    try:
                        safe_message = GuardrailsPipeline.verify_input(req.message)
                    except ValueError:
                        grd.add_event("action", "blocked")
                        metrics.metric_guardrail_blocks += 1
                        yield f"data: {json.dumps({'error': 'Message blocked by content policy.'})}\n\n"
                        return

                # 2. Cost controls ─────────────────────────────────────────────
                tracker = DynamicCostTracker(identifier)
                with Tracer(name="cost_check", session_id=session_id) as cc:
                    if await tracker.is_cost_blocked():
                        cc.add_event("circuit_breaker", "active")
                        yield f"data: {json.dumps({'error': 'System is busy conserving resources. Try again shortly.'})}\n\n"
                        return
                    if not await tracker.check_and_reserve(estimated_tokens=500):
                        cc.add_event("user_budget_exceeded", True)
                        yield f"data: {json.dumps({'error': 'Daily usage limit reached. Please try again tomorrow.'})}\n\n"
                        return

                    # 3. Semantic cache lookup ─────────────────────────────────
                    cached = await _semantic_cache.check_cache(safe_message)
                    if cached:
                        cc.add_event("cache_hit", True)
                        metrics.metric_cache_hits += 1
                        yield f"data: {json.dumps({'textChunk': cached['text']})}\n\n"
                        yield f"data: {json.dumps({'action': cached.get('action', {'type': 'none'}), 'done': True})}\n\n"
                        return
                    cc.add_event("cache_hit", False)

                # 4. Build content parts ───────────────────────────────────────
                # Merge context from request + active tasks
                ctx_parts = []
                if role:
                    ctx_parts.append(f"Role: {role}")
                active_tasks = req.context.get("activeTasks")
                if active_tasks:
                    ctx_parts.append(f"Active Tasks: {json.dumps(active_tasks)}")

                final_input = (
                    f"[Context: {' | '.join(ctx_parts)}]\n{safe_message}"
                    if ctx_parts else safe_message
                )

                content_parts = [final_input]
                if req.imageBase64 and req.imageMimeType:
                    content_parts.append(
                        {"mime_type": req.imageMimeType, "data": req.imageBase64}
                    )

                # 5. Session history + memory ──────────────────────────────────
                raw_history: list[dict] = []
                if consent:
                    raw_history = await SessionCache.get_recent_messages(session_id, limit=30)
                history = await HybridMemory.construct_relevance_history(raw_history, safe_message)

                # Apply token optimizer before LLM call
                optimized_history = TokenOptimizer.minimize_tokens(history, max_messages=10)
                formatted_history = [
                    {"role": h["role"], "parts": [h["content"]]}
                    for h in optimized_history
                ]

                # Persist user message
                if consent:
                    await SessionCache.append_message(
                        session_id, "user", safe_message,
                        user_id=identifier if not is_guest else None,
                        guest_id=identifier if is_guest else None,
                    )

                # 6. Build system prompt with live NGO data ───────────────────
                ngo_ctx: dict = {}
                if ngo_id:
                    ngo_ctx = await _fetch_ngo_context(ngo_id)
                live_context_str = _format_live_context(ngo_ctx, role, page)
                system_prompt = build_system_prompt(live_context_str)

                # 7. LLM streaming ─────────────────────────────────────────────
                with Tracer(name="llm_exec", session_id=session_id) as llm_trace:
                    response_iterator = await LLMOrchestrator.generate_response_stream(
                        formatted_history=formatted_history,
                        content_parts=content_parts,
                        system_instruction=system_prompt,
                    )

                    full_response = ""
                    token_estimate = max(len(safe_message) // 4, 1)

                    async for chunk in response_iterator:
                        text = getattr(chunk, "text", None)
                        if text:
                            full_response  += text
                            token_estimate += len(text) // 4
                            yield f"data: {json.dumps({'textChunk': text})}\n\n"

                    llm_trace.add_event("estimated_tokens", token_estimate)

                # 8. Record cost usage ─────────────────────────────────────────
                await tracker.record_usage(token_estimate)

                # 9. Output guardrails + parse action block ────────────────────
                guarded = GuardrailsPipeline.verify_output(full_response)
                action, calls, suggestions = {"type": "none"}, [], []
                match = re.search(r'```json\s*(.*?)\s*```', guarded, re.DOTALL)
                if match:
                    try:
                        parsed      = json.loads(match.group(1))
                        action      = parsed.get("action", action)
                        calls       = parsed.get("calls", calls)
                        suggestions = parsed.get("suggestions", suggestions)
                    except Exception:
                        pass

                yield f"data: {json.dumps({'action': action, 'calls': calls, 'suggestions': suggestions, 'done': True})}\n\n"

                # 10. Persist assistant reply + cache ─────────────────────────
                if consent:
                    await SessionCache.append_message(
                        session_id, "assistant", guarded,
                        user_id=identifier if not is_guest else None,
                        guest_id=identifier if is_guest else None,
                    )
                    if not action or action.get("type") == "none":
                        await _semantic_cache.save_to_cache(safe_message, guarded, action)

            except asyncio.CancelledError:
                logger.warning("Client disconnected mid-stream (session=%s).", session_id)
                metrics.metric_generator_partials += 1
                if consent and full_response:
                    await SessionCache.append_message(
                        session_id, "assistant", full_response + " [DISCONNECTED]",
                        user_id=identifier if not is_guest else None,
                        guest_id=identifier if is_guest else None,
                    )
            except Exception as exc:
                logger.error("chat_stream error (session=%s): %s", session_id, exc, exc_info=True)
                yield f"data: {json.dumps({'error': 'Platform currently unavailable. Please try again.'})}\n\n"
            finally:
                queue_manager.release(identifier, session_id)

        return StreamingResponse(event_generator(), media_type="text/event-stream")
