from __future__ import annotations
from typing import List
from asgiref.sync import sync_to_async


@sync_to_async
def _fetch_task_and_volunteers(task_id: str, ngo_id: str):
    from apps.ngo.models import Task, Assignment
    from apps.accounts.models import User, VolunteerProfile
    try:
        task = Task.objects.get(id=task_id, ngo_id=ngo_id)
    except Task.DoesNotExist:
        return None, [], {}
    rows = list(VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active"))
    # Bulk-fetch only the users whose profiles exist — O(1) queries instead of O(N)
    profile_user_ids = [p.user_id for p in rows]
    users = {u.id: u for u in User.objects.filter(id__in=profile_user_ids)}
    from django.db.models import Count
    workload_qs = (
        Assignment.objects.filter(ngo_id=ngo_id, status__in=["assigned","accepted"])
        .values("volunteer_id")
        .annotate(cnt=Count("id"))
    )
    workload = {r["volunteer_id"]: r["cnt"] for r in workload_qs}
    return task, rows, workload, users


async def rank_volunteers(task_id: str, ngo_id: str) -> List[dict]:
    result = await _fetch_task_and_volunteers(task_id, ngo_id)
    if len(result) == 3:
        return []
    task, profiles, workload, users = result

    if not task:
        return []

    required = set(s.lower().strip() for s in (task.required_skills or []))
    ranked = []

    for profile in profiles:
        user = users.get(profile.user_id)
        if not user:
            continue
        vol_skills = set(s.lower().strip() for s in (profile.skills or []))
        matched = required & vol_skills

        skill_score = (len(matched) / len(required)) if required else 1.0
        avail = profile.availability or {}
        days_available = sum(1 for v in avail.values() if v)
        avail_score = min(days_available / 7, 1.0)
        wl = workload.get(user.id, 0)
        wl_score = max(0.0, 1.0 - (wl / 5))
        final = round(skill_score * 0.5 + avail_score * 0.3 + wl_score * 0.2, 3)

        ranked.append({
            "volunteer_id": user.id,
            "email": user.email,
            "name": user.email.split("@")[0],
            "score": final,
            "matched_skills": sorted(matched),
            "missing_skills": sorted(required - vol_skills),
            "workload": wl,
            "available_days": days_available,
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)
