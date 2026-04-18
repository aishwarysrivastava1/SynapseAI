from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models import User, VolunteerProfile, Assignment, Task
from typing import List


async def rank_volunteers(task_id: str, ngo_id: str, db: AsyncSession) -> List[dict]:
    """
    Heuristic scoring:
      skill_match  × 0.5  — fraction of required skills the volunteer has
      availability × 0.3  — fraction of weekdays marked available
      workload     × 0.2  — penalty for current open assignments (caps at 5)

    Returns list sorted by score desc.
    """
    task = await db.get(Task, task_id)
    if not task or task.ngo_id != ngo_id:
        return []

    required = set(s.lower().strip() for s in (task.required_skills or []))

    # Fetch all active volunteer profiles in this NGO with their users
    result = await db.execute(
        select(User, VolunteerProfile)
        .join(VolunteerProfile, VolunteerProfile.user_id == User.id)
        .where(User.ngo_id == ngo_id, VolunteerProfile.status == "active")
    )
    rows = result.fetchall()

    # Fetch workload counts (open assignments)
    wl_result = await db.execute(
        select(Assignment.volunteer_id, func.count().label("cnt"))
        .where(
            Assignment.ngo_id == ngo_id,
            Assignment.status.in_(["assigned", "accepted"]),
        )
        .group_by(Assignment.volunteer_id)
    )
    workload: dict[str, int] = {r.volunteer_id: r.cnt for r in wl_result}

    ranked = []
    for user, profile in rows:
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
            "volunteer_id":   user.id,
            "email":          user.email,
            "name":           user.email.split("@")[0],
            "score":          final,
            "matched_skills": sorted(matched),
            "missing_skills": sorted(required - vol_skills),
            "workload":       wl,
            "available_days": days_available,
        })

    return sorted(ranked, key=lambda x: x["score"], reverse=True)
