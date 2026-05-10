import json
import logging
import queue
import threading
import uuid

from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.core.authentication import SynapseJWTAuthentication

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Saathi, the Autonomous AI Assistant for Sanchaalan Saathi — an NGO volunteer and resource management platform. Help users manage volunteers, tasks, and resources. Keep responses under 200 words. Be concise and actionable."""

_DONE = object()  # sentinel for sync generator


class ChatStreamView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [SynapseJWTAuthentication]

    def post(self, request):
        req_id = str(uuid.uuid4())
        message = request.data.get("message", "")
        context = request.data.get("context", {})
        image_b64 = request.data.get("imageBase64")
        image_mime = request.data.get("imageMimeType")

        user = getattr(request, "user", None)
        is_auth = user and getattr(user, "is_authenticated", False)
        identifier = user.user_id if is_auth else getattr(request, "guest_id", "anonymous")

        from services.chatbot.observability import request_id_var
        request_id_var.set(req_id)

        out: queue.Queue = queue.Queue()

        async def _collect():
            from services.chatbot.cost_control import DynamicCostTracker
            from services.chatbot.guardrails import GuardrailsPipeline
            from services.chatbot.cache import SemanticCache
            from services.chatbot.memory import HybridMemory
            from services.chatbot.llm import LLMOrchestrator

            try:
                cost_tracker = DynamicCostTracker(identifier=identifier)
                budget_ok = await cost_tracker.check_and_reserve(estimated_tokens=500)
                if not budget_ok:
                    out.put(f"data: {json.dumps({'error': 'Daily token budget exceeded. Try again tomorrow.'})}\n\n")
                    return

                guardrails = GuardrailsPipeline()
                safe, reason = await guardrails.check_input(message)
                if not safe:
                    out.put(f"data: {json.dumps({'error': f'Message blocked: {reason}'})}\n\n")
                    return

                sem_cache = SemanticCache()
                cached = await sem_cache.get(message)
                if cached:
                    for word in cached.get("reply_text", "").split():
                        out.put(f"data: {json.dumps({'textChunk': word + ' '})}\n\n")
                    out.put(f"data: {json.dumps({'done': True, 'action_response': cached.get('action_response', {})})}\n\n")
                    return

                memory = HybridMemory(identifier=identifier)
                history = await memory.get_recent(limit=10)

                orchestrator = LLMOrchestrator()
                full_reply = ""
                action_response = {}

                async for chunk in orchestrator.stream(
                    system_prompt=SYSTEM_PROMPT,
                    history=history,
                    user_message=message,
                    context=context,
                    image_b64=image_b64,
                    image_mime=image_mime,
                ):
                    if isinstance(chunk, dict):
                        action_response = chunk
                    else:
                        full_reply += chunk
                        out.put(f"data: {json.dumps({'textChunk': chunk})}\n\n")

                await memory.add(role="user", content=message)
                await memory.add(role="assistant", content=full_reply)
                await sem_cache.store(message, full_reply, action_response)
                await cost_tracker.record_usage(tokens_used=len(full_reply.split()) * 2)

                out.put(f"data: {json.dumps({'done': True, 'action_response': action_response})}\n\n")

            except Exception as e:
                logger.error("Chat stream error: %s", e, exc_info=True)
                out.put(f"data: {json.dumps({'error': 'Stream error. Please try again.'})}\n\n")
            finally:
                out.put(_DONE)

        def _run_async():
            from asgiref.sync import async_to_sync
            async_to_sync(_collect)()

        threading.Thread(target=_run_async, daemon=True).start()

        def sync_generator():
            while True:
                item = out.get()
                if item is _DONE:
                    break
                yield item

        response = StreamingHttpResponse(sync_generator(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class MetricsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        lines = [
            "# HELP chatbot_requests_total Total chatbot requests",
            "# TYPE chatbot_requests_total counter",
            "chatbot_requests_total 0",
        ]
        return HttpResponse("\n".join(lines) + "\n",
                            content_type="text/plain; version=0.0.4; charset=utf-8")
