import logging
import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import GlobalResourceCounter

logger = logging.getLogger(__name__)

class BackpressureManager:
    """
    Stateless, DB-backed Concurrency Engine.
    Enforces limits across distributed serverless instances using atomic conditional updates.
    """
    def __init__(self, global_limit=100, max_queue=500, max_per_user=5, max_per_session=2):
        self.global_limit = global_limit
        self.max_queue = max_queue # We'll treat this as a soft limit for now
        self.max_per_user = max_per_user
        self.max_per_session = max_per_session
        self.epoch = datetime.datetime(2000, 1, 1) # Constant for uq_res_ts compatibility

    async def _atomic_acquire(self, db: AsyncSession, key: str, max_limit: int) -> bool:
        """Atomic incremental acquire with conditional bound check."""
        expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=5) # 5m lock TTL
        
        stmt = (
            insert(GlobalResourceCounter)
            .values(
                resource_key=key,
                timestamp_minute=self.epoch,
                current_value=1,
                expires_at=expires
            )
            .on_conflict_do_update(
                constraint="uq_res_ts",
                set_={
                    "current_value": GlobalResourceCounter.current_value + 1,
                    "expires_at": expires
                },
                where=(GlobalResourceCounter.current_value < max_limit)
            )
            .returning(GlobalResourceCounter.current_value)
        )
        
        try:
            result = await db.execute(stmt)
            val = result.scalar()
            if val is not None:
                return True
            return False
        except Exception as e:
            logger.error(f"Concurrency acquire failure for {key}: {e}")
            return False

    async def _atomic_release(self, db: AsyncSession, key: str):
        """Decrement counter atomically."""
        stmt = (
            update(GlobalResourceCounter)
            .where(GlobalResourceCounter.resource_key == key, GlobalResourceCounter.timestamp_minute == self.epoch)
            .where(GlobalResourceCounter.current_value > 0)
            .values(current_value=GlobalResourceCounter.current_value - 1)
        )
        try:
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.error(f"Concurrency release failure for {key}: {e}")

    async def acquire(self, db: AsyncSession, user_id: str, session_id: str) -> None:
        """
        Hardened Acquire:
        1. Check/Reserve Global Slot
        2. Check/Reserve User Slot
        3. Check/Reserve Session Slot
        """
        # 1. Global Concurrency
        if not await self._atomic_acquire(db, "conc:global", self.global_limit):
            raise ValueError("Global system capacity reached. Please retry in a moment.")

        # 2. User Concurrency
        if not await self._atomic_acquire(db, f"conc:user:{user_id}", self.max_per_user):
            # Rollback global if user fails
            await self._atomic_release(db, "conc:global")
            raise ValueError("You have too many active chat requests. Await completion.")

        # 3. Session Concurrency
        if not await self._atomic_acquire(db, f"conc:sess:{session_id}", self.max_per_session):
            # Rollback previous if session fails
            await self._atomic_release(db, "conc:global")
            await self._atomic_release(db, f"conc:user:{user_id}")
            raise ValueError("Multiple queries detected in this session. Await the first response.")

        await db.commit()
        logger.info(f"Slots reserved for {user_id} | {session_id}")

    async def release(self, db: AsyncSession, user_id: str, session_id: str) -> None:
        """Explicitly release all reserved slots."""
        # Note: We don't commit until all 3 are done to minimize round-trips if possible,
        # but _atomic_release handles its own commit for safety.
        await self._atomic_release(db, "conc:global")
        await self._atomic_release(db, f"conc:user:{user_id}")
        await self._atomic_release(db, f"conc:sess:{session_id}")
        logger.info(f"Slots released for {user_id} | {session_id}")

# Global Singleton Manager instance 
queue_manager = BackpressureManager()
