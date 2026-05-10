from asgiref.sync import sync_to_async


@sync_to_async
def get_consent_flags(user_id: str) -> dict:
    from apps.accounts.models import User
    user = User.objects.filter(id=user_id).values(
        "consent_analytics", "consent_personalization", "consent_ai_training"
    ).first()
    if not user:
        return {"analytics": False, "personalization": False, "ai_training": False}
    return {
        "analytics": bool(user["consent_analytics"]),
        "personalization": bool(user["consent_personalization"]),
        "ai_training": bool(user["consent_ai_training"]),
    }
