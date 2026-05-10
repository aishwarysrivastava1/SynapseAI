import uuid
from django.db import models


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class ChatbotSession(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    user_id = models.CharField(max_length=36, null=True, blank=True)
    guest_id = models.CharField(max_length=36, null=True, blank=True)
    ngo_id = models.CharField(max_length=36, null=True, blank=True)
    channel = models.CharField(max_length=40, default="web")
    language = models.CharField(max_length=32, default="en")
    context_tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chatbot_sessions"
        indexes = [
            models.Index(fields=["user_id"],  name="ix_chatbot_session_user_id"),
            models.Index(fields=["ngo_id"],   name="ix_chatbot_session_ngo_id"),
            models.Index(fields=["guest_id"], name="ix_chatbot_session_guest_id"),
        ]


class ChatbotMessage(models.Model):
    ROLE_CHOICES = [("user", "user"), ("assistant", "assistant"), ("system", "system")]

    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    session_id = models.CharField(max_length=36)
    user_id = models.CharField(max_length=36, null=True, blank=True)
    guest_id = models.CharField(max_length=36, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    prompt_features = models.JSONField(default=dict)
    latency_ms = models.IntegerField(null=True, blank=True)
    user_feedback = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chatbot_messages"
        indexes = [
            models.Index(fields=["session_id"],          name="ix_chatbot_msg_session_id"),
            models.Index(fields=["role"],                 name="ix_chatbot_msg_role"),
            models.Index(fields=["session_id", "role"],   name="ix_chatbot_msg_session_role"),
        ]


class ChatbotSemanticCache(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    input_hash = models.CharField(max_length=64)
    embedding = models.JSONField(default=list)
    action_response = models.JSONField(default=dict)
    reply_text = models.TextField()
    intent_category = models.CharField(max_length=100, null=True, blank=True)
    hits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chatbot_semantic_cache"
        indexes = [
            models.Index(fields=["input_hash"], name="ix_semantic_cache_hash"),
            models.Index(fields=["hits"], name="ix_semantic_cache_hits"),
            models.Index(fields=["updated_at"], name="ix_semantic_cache_updated"),
        ]


class TokenUsageCounter(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    identifier = models.CharField(max_length=100)
    date_stamp = models.DateField()
    session_id = models.CharField(max_length=36, null=True, blank=True)
    total_tokens = models.IntegerField(default=0)
    requests_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "token_usage_counters"
        indexes = [
            models.Index(fields=["identifier"], name="ix_token_usage_user"),
            models.Index(fields=["date_stamp"], name="ix_token_usage_date"),
        ]


class GlobalResourceCounter(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=_gen_uuid)
    resource_key = models.CharField(max_length=120)
    timestamp_minute = models.DateTimeField(db_index=True)
    current_value = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "global_resource_counters"
        constraints = [
            models.UniqueConstraint(
                fields=["resource_key", "timestamp_minute"],
                name="uq_res_ts",
            )
        ]
        indexes = [
            models.Index(fields=["timestamp_minute"], name="ix_global_res_ts"),
            models.Index(fields=["expires_at"], name="ix_global_res_expires"),
        ]
