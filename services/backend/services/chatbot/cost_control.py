import os
import datetime
import logging

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

USER_DAILY_TOKEN_LIMIT = int(os.getenv("USER_DAILY_TOKEN_LIMIT", 20000))
GLOBAL_TPM_LIMIT = int(os.getenv("GLOBAL_TPM_LIMIT", 50000))


@sync_to_async
def _get_or_create_daily_usage(identifier: str, date_stamp) -> tuple:
    from apps.chatbot.models import TokenUsageCounter
    obj, created = TokenUsageCounter.objects.get_or_create(
        identifier=identifier, date_stamp=date_stamp,
        defaults={"total_tokens": 0, "requests_count": 0},
    )
    return obj, created


@sync_to_async
def _increment_usage(identifier: str, date_stamp, tokens: int) -> int:
    from django.db.models import F
    from apps.chatbot.models import TokenUsageCounter
    obj, _ = TokenUsageCounter.objects.get_or_create(
        identifier=identifier, date_stamp=date_stamp,
        defaults={"total_tokens": 0, "requests_count": 0},
    )
    TokenUsageCounter.objects.filter(id=obj.id).update(
        total_tokens=F("total_tokens") + tokens,
        requests_count=F("requests_count") + 1,
    )
    obj.refresh_from_db()
    return obj.total_tokens


@sync_to_async
def _increment_global_tpm(tokens: int) -> int:
    from django.db.models import F
    from apps.chatbot.models import GlobalResourceCounter
    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None).replace(second=0, microsecond=0)
    obj, _ = GlobalResourceCounter.objects.get_or_create(
        resource_key="gemini_tpm", timestamp_minute=now,
        defaults={"current_value": 0},
    )
    GlobalResourceCounter.objects.filter(id=obj.id).update(
        current_value=F("current_value") + tokens
    )
    obj.refresh_from_db()
    return obj.current_value


@sync_to_async
def _check_global_tpm() -> int:
    from apps.chatbot.models import GlobalResourceCounter
    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None).replace(second=0, microsecond=0)
    obj = GlobalResourceCounter.objects.filter(
        resource_key="gemini_tpm", timestamp_minute=now
    ).first()
    return obj.current_value if obj else 0


class DynamicCostTracker:
    def __init__(self, identifier: str):
        self.identifier = identifier

    async def check_and_reserve(self, estimated_tokens: int = 500) -> bool:
        today = datetime.date.today()
        obj, _ = await _get_or_create_daily_usage(self.identifier, today)
        if obj.total_tokens + estimated_tokens > USER_DAILY_TOKEN_LIMIT:
            logger.warning("User %s daily token limit hit", self.identifier)
            return False
        tpm = await _check_global_tpm()
        if tpm >= GLOBAL_TPM_LIMIT:
            logger.error("Global TPM limit hit: %s", tpm)
            return False
        return True

    async def record_usage(self, tokens_used: int) -> None:
        today = datetime.date.today()
        new_total = await _increment_usage(self.identifier, today, tokens_used)
        await _increment_global_tpm(tokens_used)
        if new_total > USER_DAILY_TOKEN_LIMIT * 0.8:
            logger.warning("User %s at 80%% daily token limit: %s", self.identifier, new_total)

    async def is_cost_blocked(self) -> bool:
        tpm = await _check_global_tpm()
        return tpm >= GLOBAL_TPM_LIMIT
