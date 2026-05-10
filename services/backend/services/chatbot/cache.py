from __future__ import annotations

import asyncio
import hashlib
import logging

from asgiref.sync import sync_to_async
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Google Gemini text embedding using models/text-embedding-004."""

    MODEL = "models/text-embedding-004"

    @staticmethod
    async def get_embedding(text: str) -> list[float]:
        if not text:
            return []
        try:
            import google.generativeai as genai
            result = await asyncio.to_thread(
                genai.embed_content,
                model=EmbeddingProvider.MODEL,
                content=text,
                task_type="semantic_similarity",
            )
            return result["embedding"]
        except Exception as exc:
            logger.warning("Embedding generation failed (will skip cache): %s", exc)
            return []


# ── Django ORM helpers (sync_to_async) ───────────────────────────────────────

@sync_to_async
def _query_cache(intent: str, limit: int = 20) -> list:
    from apps.chatbot.models import ChatbotSemanticCache
    return list(
        ChatbotSemanticCache.objects.filter(intent_category=intent)
        .order_by("-hits")
        .values("id", "input_hash", "embedding", "reply_text", "action_response", "hits")[:limit]
    )


@sync_to_async
def _increment_cache_hits(cache_id: str) -> None:
    from django.db.models import F
    from apps.chatbot.models import ChatbotSemanticCache
    ChatbotSemanticCache.objects.filter(id=cache_id).update(hits=F("hits") + 1)


@sync_to_async
def _store_cache(
    input_hash: str,
    embedding: list,
    reply_text: str,
    action_response: dict,
    intent: str,
) -> None:
    from apps.chatbot.models import ChatbotSemanticCache
    ChatbotSemanticCache.objects.update_or_create(
        input_hash=input_hash,
        defaults={
            "embedding":       embedding,
            "reply_text":      reply_text,
            "action_response": action_response,
            "intent_category": intent,
        },
    )


# ── SemanticCache ─────────────────────────────────────────────────────────────

class SemanticCache:
    """
    Semantic similarity cache backed by Django ORM + Gemini embeddings.

    Provides both instance-method API (get / store) and the call-site aliases
    used by chatbot_routes (check_cache / save_to_cache).
    """

    SIMILARITY_THRESHOLD = 0.85

    async def get(self, prompt: str, intent_category: str = "general") -> dict | None:
        """Return cached response if a semantically similar prompt exists."""
        embedding = await EmbeddingProvider.get_embedding(prompt)
        if not embedding:
            return None
        try:
            rows = await _query_cache(intent_category)
            best_score = 0.0
            best_row: dict | None = None
            for row in rows:
                cached_emb = row.get("embedding") or []
                if not cached_emb or len(cached_emb) != len(embedding):
                    continue
                score = 1.0 - cosine(embedding, cached_emb)
                if score > best_score:
                    best_score = score
                    best_row = row
            if best_row and best_score >= self.SIMILARITY_THRESHOLD:
                await _increment_cache_hits(best_row["id"])
                return {
                    "text":   best_row["reply_text"],
                    "action": best_row.get("action_response") or {"type": "none"},
                }
        except Exception as exc:
            logger.error("SemanticCache.get failed: %s", exc)
        return None

    async def store(
        self,
        prompt: str,
        reply_text: str,
        action_response: dict,
        intent_category: str = "general",
    ) -> None:
        """Persist a prompt→response pair for future cache hits."""
        embedding = await EmbeddingProvider.get_embedding(prompt)
        input_hash = hashlib.sha256(prompt.encode()).hexdigest()[:64]
        try:
            await _store_cache(input_hash, embedding, reply_text, action_response, intent_category)
        except Exception as exc:
            logger.error("SemanticCache.store failed: %s", exc)

    # ── Aliases matching chatbot_routes.py call sites ─────────────────────────

    async def check_cache(self, prompt: str, intent_category: str = "general") -> dict | None:
        return await self.get(prompt, intent_category)

    async def save_to_cache(
        self,
        prompt: str,
        reply_text: str,
        action_response: dict,
        intent_category: str = "general",
    ) -> None:
        await self.store(prompt, reply_text, action_response, intent_category)

    # Legacy alias
    async def cache_response(
        self,
        prompt: str,
        reply_text: str,
        action_response: dict,
        intent_category: str = "general",
    ) -> None:
        await self.store(prompt, reply_text, action_response, intent_category)
