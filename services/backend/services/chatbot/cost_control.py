import os
import datetime
import logging
from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from db.models import TokenUsageCounter, GlobalResourceCounter

logger = logging.getLogger(__name__)

# Environment-driven dynamic configuration
USER_DAILY_TOKEN_LIMIT = int(os.getenv("USER_DAILY_TOKEN_LIMIT", 20000))
GLOBAL_TPM_LIMIT = int(os.getenv("GLOBAL_TPM_LIMIT", 50000))

class DynamicCostTracker:
    @staticmethod
    async def increment_global_tpm(db: AsyncSession, tokens: int) -> int:
        """
        Atomically increment the global TPM counter in PostgreSQL.
        Returns the new total for the current minute.
        """
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        stmt = (
            insert(GlobalResourceCounter)
            .values(
                resource_key="gemini_tpm",
                timestamp_minute=now,
                current_value=tokens
            )
            .on_conflict_do_update(
                constraint="uq_res_ts",
                set_={"current_value": GlobalResourceCounter.current_value + tokens}
            )
            .returning(GlobalResourceCounter.current_value)
        )
        try:
            result = await db.execute(stmt)
            val = result.scalar() or tokens
            if val >= GLOBAL_TPM_LIMIT:
                logger.error(f"GLOBAL TPM LIMIT HIT: {val} >= {GLOBAL_TPM_LIMIT}. System throttling engaged.")
            return val
        except Exception as e:
            logger.error(f"Failed to increment global TPM: {e}")
            return 0

    @staticmethod
    async def is_cost_blocked(db: AsyncSession) -> bool:
        """
        Check if the global TPM for the current minute is already over the limit.
        """
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        stmt = select(GlobalResourceCounter.current_value).where(
            GlobalResourceCounter.resource_key == "gemini_tpm",
            GlobalResourceCounter.timestamp_minute == now
        )
        try:
            result = await db.execute(stmt)
            val = result.scalar() or 0
            return val >= GLOBAL_TPM_LIMIT
        except Exception:
            return False

    @staticmethod
    async def check_user_budget(db: AsyncSession, identifier: str) -> bool:
        """
        Verify if an individual user has blown past their specific daily allocation.
        """
        if not db:
            return True # Ephemeral mode doesn't track DB limits
            
        today = datetime.datetime.utcnow().date()
        stmt = select(TokenUsageCounter.total_tokens).where(
            TokenUsageCounter.identifier == identifier,
            TokenUsageCounter.date_stamp == today
        )
        try:
            result = await db.execute(stmt)
            total = result.scalar() or 0
            if total > USER_DAILY_TOKEN_LIMIT:
                logger.warning(f"User {identifier} exceeded daily token budget ({total} > {USER_DAILY_TOKEN_LIMIT})")
                return False
            return True
        except Exception:
            return True

    @staticmethod
    async def record_usage(db: AsyncSession, identifier: str, session_id: str, tokens: int):
        """
        Record usage natively per user and increment global TPM.
        """
        # 1. Increment Global TPM
        await DynamicCostTracker.increment_global_tpm(db, tokens)
        
        # 2. Update User Daily Budget
        if not db:
            return 

        today = datetime.datetime.utcnow().date()
        stmt = (
            insert(TokenUsageCounter)
            .values(
                identifier=identifier,
                date_stamp=today,
                session_id=session_id,
                total_tokens=tokens,
                requests_count=1
            )
            .on_conflict_do_update(
                index_elements=["identifier", "date_stamp"],
                set_={
                    "total_tokens": TokenUsageCounter.total_tokens + tokens,
                    "requests_count": TokenUsageCounter.requests_count + 1,
                    "updated_at": datetime.datetime.utcnow()
                }
            )
        )
        try:
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to record token usage: {e}")
            await db.rollback()
