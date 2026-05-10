import time
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class LruCache:
    def __init__(self, capacity: int, ttl_seconds: int):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.cache = {}

    def get(self, key: str):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache[key] = self.cache.pop(key)
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value):
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = (value, time.time())

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]


_memory_cache = LruCache(capacity=5000, ttl_seconds=300)


@sync_to_async
def _get_or_create_session_sync(identifier: str, is_guest: bool, context_tags: list) -> object:
    from apps.chatbot.models import ChatbotSession
    from apps.guest.models import Guest
    if is_guest:
        Guest.objects.get_or_create(id=identifier)
        session = ChatbotSession.objects.filter(
            guest_id=identifier
        ).order_by("-created_at").first()
        if not session:
            session = ChatbotSession.objects.create(
                guest_id=identifier, context_tags=context_tags or []
            )
    else:
        session = ChatbotSession.objects.filter(
            user_id=identifier
        ).order_by("-created_at").first()
        if not session:
            session = ChatbotSession.objects.create(
                user_id=identifier, context_tags=context_tags or []
            )
    return session


@sync_to_async
def _get_messages_sync(session_id: str, limit: int) -> list:
    from apps.chatbot.models import ChatbotMessage
    msgs = list(ChatbotMessage.objects.filter(
        session_id=session_id
    ).order_by("-created_at")[:limit])
    return [
        {"role": m.role if m.role == "user" else "model", "content": m.content}
        for m in reversed(msgs)
    ]


@sync_to_async
def _append_message_sync(session_id: str, role: str, content: str,
                          user_id: str | None, guest_id: str | None) -> None:
    from apps.chatbot.models import ChatbotMessage
    ChatbotMessage.objects.create(
        session_id=session_id,
        user_id=user_id, guest_id=guest_id,
        role=role if role == "user" else "assistant",
        content=content,
    )


class SessionCache:
    @staticmethod
    async def get_or_create_session(identifier: str, is_guest: bool, context_tags: list = None):
        return await _get_or_create_session_sync(identifier, is_guest, context_tags)

    @staticmethod
    async def get_recent_messages(session_id: str, limit: int = 14) -> list[dict]:
        cache_key = f"msgs_{session_id}"
        cached = _memory_cache.get(cache_key)
        if cached is not None:
            return cached
        history = await _get_messages_sync(session_id, limit)
        _memory_cache.set(cache_key, history)
        return history

    @staticmethod
    async def append_message(session_id: str, role: str, content: str,
                              user_id: str | None = None, guest_id: str | None = None) -> None:
        await _append_message_sync(session_id, role, content, user_id, guest_id)
        _memory_cache.delete(f"msgs_{session_id}")
