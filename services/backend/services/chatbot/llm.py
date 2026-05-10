from __future__ import annotations

import asyncio
import logging
import os
import random

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Accept both env var names; GEM_KEY takes precedence for backward compat
_API_KEY = os.environ.get("GEM_KEY") or os.environ.get("GEMINI_API_KEY") or ""

if not _API_KEY:
    logger.warning(
        "No Gemini API key found. Set GEM_KEY or GEMINI_API_KEY. "
        "Chatbot will fail until a key is provided."
    )

genai.configure(api_key=_API_KEY)

# Safety: allow humanitarian/emergency discussion; only block explicit harm
_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",        "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",  "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",  "threshold": "BLOCK_ONLY_HIGH"},
]

_GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=0.7,
    top_p=0.9,
    max_output_tokens=1024,
)


class LLMOrchestrator:
    """
    Manages model fallback cascading, jittered exponential backoff, and robust
    streaming response generation via Google Gemini.
    """
    MAX_RETRIES = 3
    PRIMARY_MODEL  = "gemini-2.0-flash"        # stable production model
    FALLBACK_MODEL = "gemini-1.5-flash"         # fast fallback

    @staticmethod
    async def generate_response_stream(
        formatted_history: list,
        content_parts: list,
        system_instruction: str,
    ):
        """
        Returns an async iterable of Gemini response chunks.
        Falls back from PRIMARY → FALLBACK model on repeated errors.
        Uses jittered exponential backoff to avoid thundering herd.
        """
        attempt = 0
        current_model = LLMOrchestrator.PRIMARY_MODEL

        while attempt < LLMOrchestrator.MAX_RETRIES:
            try:
                model = genai.GenerativeModel(
                    current_model,
                    system_instruction=system_instruction,
                    safety_settings=_SAFETY_SETTINGS,
                    generation_config=_GENERATION_CONFIG,
                )
                chat = model.start_chat(history=formatted_history)
                stream = await chat.send_message_async(content_parts, stream=True)
                return stream
            except Exception as exc:
                attempt += 1
                # Jittered backoff: base 2^attempt + uniform(0, 1)
                wait = min(2 ** attempt + random.uniform(0.0, 1.0), 30.0)
                logger.warning(
                    "LLM attempt %d/%d failed (%s). Retrying in %.1fs.",
                    attempt, LLMOrchestrator.MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)

                if attempt >= 2 and current_model != LLMOrchestrator.FALLBACK_MODEL:
                    logger.info("Cascading to fallback model: %s", LLMOrchestrator.FALLBACK_MODEL)
                    current_model = LLMOrchestrator.FALLBACK_MODEL

        logger.error("LLM exhausted %d retries. Raising.", LLMOrchestrator.MAX_RETRIES)
        raise RuntimeError("Generative service unavailable after retries.")


async def verify_gemini_key() -> bool:
    """
    Called at startup to confirm the API key is valid.
    Returns True on success, False (with log) on failure.
    """
    if not _API_KEY:
        logger.error("Gemini API key missing — chatbot will not work.")
        return False
    try:
        model = genai.GenerativeModel(LLMOrchestrator.FALLBACK_MODEL)
        await asyncio.to_thread(model.generate_content, "ping")
        logger.info("Gemini API key verified OK (model: %s).", LLMOrchestrator.FALLBACK_MODEL)
        return True
    except Exception as exc:
        logger.error("Gemini API key verification failed: %s", exc)
        return False
