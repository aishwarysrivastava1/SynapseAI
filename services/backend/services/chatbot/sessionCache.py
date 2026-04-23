import time
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import ChatbotSession, ChatbotMessage, Guest

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
                # Move to end to show it was recently used
                self.cache[key] = self.cache.pop(key)
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: any):
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            # Pop first item
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = (value, time.time())

    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]

# Fast memory mapping to offload DB calls
_memory_cache = LruCache(max_size:=5000, ttl:=300) 

class SessionCache:
    """
    PostgreSQL-backed session persistence + optional in-memory LRU.
    """
    
    @staticmethod
    async def get_or_create_session(db: AsyncSession, identifier: str, is_guest: bool, context_tags: list = None) -> ChatbotSession:
        if is_guest:
            # Ensure guest exists
            from db.models import Guest
            guest = (await db.execute(select(Guest).where(Guest.id == identifier))).scalar_one_or_none()
            if not guest:
                guest = Guest(id=identifier)
                db.add(guest)
                await db.commit()
                await db.refresh(guest)
                
            session = (await db.execute(select(ChatbotSession).where(ChatbotSession.guest_id == identifier).order_by(ChatbotSession.created_at.desc()))).scalars().first()
            if not session:
                session = ChatbotSession(guest_id=identifier, context_tags=context_tags or [])
                db.add(session)
                await db.commit()
                await db.refresh(session)
        else:
            session = (await db.execute(select(ChatbotSession).where(ChatbotSession.user_id == identifier).order_by(ChatbotSession.created_at.desc()))).scalars().first()
            if not session:
                session = ChatbotSession(user_id=identifier, context_tags=context_tags or [])
                db.add(session)
                await db.commit()
                await db.refresh(session)
        return session

    @staticmethod
    async def get_recent_messages(db: AsyncSession, session_id: str, limit: int = 14) -> list[dict]:
        cache_key = f"msgs_{session_id}"
        cached = _memory_cache.get(cache_key)
        if cached is not None:
            return cached

        res = await db.execute(
            select(ChatbotMessage)
            .where(ChatbotMessage.session_id == session_id)
            .order_by(ChatbotMessage.created_at.desc())
            .limit(limit)
        )
        msgs = res.scalars().all()
        # reverse so it's chronologically forward
        history = [
            {"role": m.role if m.role == "user" else "model", "content": m.content} 
            for m in reversed(msgs)
        ]
        
        _memory_cache.set(cache_key, history)
        return history

    @staticmethod
    async def append_message(db: AsyncSession, session_id: str, role: str, content: str, user_id: str = None, guest_id: str = None):
        msg = ChatbotMessage(
            session_id=session_id,
            user_id=user_id,
            guest_id=guest_id,
            role=role if role == "user" else "assistant",
            content=content
        )
        db.add(msg)
        await db.commit()
        
        # Invalidate cache for this session
        cache_key = f"msgs_{session_id}"
        _memory_cache.delete(cache_key)
