from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from db.base import get_db
from db.models import User, VolunteerProfile, Task, Assignment, Notification
from middleware.rbac import CurrentUser, require_volunteer

router = APIRouter()


# ── Pydantic models ──────────────────────────────────────────────────────────

class ProfileUpdateReq(BaseModel):
    skills:       Optional[List[str]] = None
    availability: Optional[dict]      = None  # {"mon": true, ..., "sun": false}


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def vol_dashboard(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    assigned = (await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
            Assignment.status.in_(["assigned", "accepted"]),
        )
    )).scalar() or 0

    completed = (await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
            Assignment.status == "completed",
        )
    )).scalar() or 0

    unread_notifs = (await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.user_id, Notification.is_read == False  # noqa: E712
        )
    )).scalar() or 0

    # Upcoming deadlines (open assignments)
    upcoming_rows = (await db.execute(
        select(Task, Assignment)
        .join(Assignment, Assignment.task_id == Task.id)
        .where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
            Assignment.status.in_(["assigned", "accepted"]),
            Task.deadline != None,  # noqa: E711
        )
        .order_by(Task.deadline.asc())
        .limit(5)
    )).fetchall()

    deadlines = [
        {"task_id": t.id, "title": t.title, "deadline": t.deadline, "assignment_status": a.status}
        for t, a in upcoming_rows
    ]

    # Assignments list for dashboard display
    assignment_rows = (await db.execute(
        select(Task, Assignment)
        .join(Assignment, Assignment.task_id == Task.id)
        .where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
        .order_by(Assignment.assigned_at.desc())
        .limit(10)
    )).fetchall()

    assignments = [
        {
            "id":               a.id,
            "task_title":       t.title,
            "task_description": t.description,
            "required_skills":  t.required_skills,
            "status":           a.status,
            "deadline":         t.deadline,
            "assigned_at":      a.assigned_at,
        }
        for t, a in assignment_rows
    ]

    return {
        "assigned_tasks":        assigned,
        "completed_tasks":       completed,
        "unread_notifications":  unread_notifs,
        "upcoming_deadlines":    deadlines,
        "assignments":           assignments,
    }


# ── Profile ──────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    u = await db.get(User, user.user_id)
    p = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user.user_id)
    )).scalar_one_or_none()

    # Performance stats
    total_assigned = (await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
            Assignment.status != "assigned",
        )
    )).scalar() or 0

    completed_count = (await db.execute(
        select(func.count()).select_from(Assignment).where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
            Assignment.status == "completed",
        )
    )).scalar() or 0

    acceptance_rate  = round(completed_count / max(total_assigned, 1), 4)
    performance_score = round(acceptance_rate * 100, 1)

    return {
        "user_id":          user.user_id,
        "email":            u.email if u else user.email,
        "ngo_id":           user.ngo_id,
        "skills":           p.skills       if p else [],
        "availability":     p.availability if p else {},
        "status":           p.status       if p else "active",
        "completed_tasks":  completed_count,
        "total_assigned":   total_assigned,
        "acceptance_rate":  acceptance_rate,
        "performance_score": performance_score,
    }


@router.put("/profile")
async def update_profile(
    req: ProfileUpdateReq,
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    p = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user.user_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    if req.skills is not None:       p.skills = req.skills
    if req.availability is not None: p.availability = req.availability
    return {"message": "Profile updated"}


# ── Tasks & Assignments ──────────────────────────────────────────────────────

@router.get("/tasks")
async def get_my_tasks(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Task, Assignment)
        .join(Assignment, Assignment.task_id == Task.id)
        .where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
        .order_by(Assignment.assigned_at.desc())
    )).fetchall()

    return [
        {
            "task_id":           t.id,
            "title":             t.title,
            "description":       t.description,
            "required_skills":   t.required_skills,
            "task_status":       t.status,
            "deadline":          t.deadline,
            "assignment_id":     a.id,
            "assignment_status": a.status,
            "assigned_at":       a.assigned_at,
        }
        for t, a in rows
    ]


@router.get("/assignments")
async def get_my_assignments(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Assignment).where(
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
        .order_by(Assignment.assigned_at.desc())
    )).scalars().all()
    return [
        {"id": a.id, "task_id": a.task_id, "status": a.status, "assigned_at": a.assigned_at}
        for a in rows
    ]


@router.post("/assignments/{assignment_id}/accept")
async def accept_assignment(
    assignment_id: str,
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    a = (await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if a.status != "assigned":
        raise HTTPException(status_code=400, detail=f"Cannot accept — current status: {a.status}")

    a.status = "accepted"

    # Notify NGO admin
    task = await db.get(Task, a.task_id)
    admin = (await db.execute(
        select(User).where(User.ngo_id == user.ngo_id, User.role == "ngo_admin")
    )).scalar_one_or_none()
    if admin and task:
        db.add(Notification(
            user_id=admin.id,
            message=f"Volunteer accepted task: {task.title}",
            type="status_update",
        ))
    return {"status": "accepted"}


@router.post("/assignments/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    a = (await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if a.status not in ("assigned", "accepted"):
        raise HTTPException(status_code=400, detail=f"Cannot reject — current status: {a.status}")

    a.status = "rejected"

    # Reopen task only if it belongs to our NGO
    task = (await db.execute(
        select(Task).where(Task.id == a.task_id, Task.ngo_id == user.ngo_id)
    )).scalar_one_or_none()
    if task:
        task.status = "open"

    admin = (await db.execute(
        select(User).where(User.ngo_id == user.ngo_id, User.role == "ngo_admin")
    )).scalar_one_or_none()
    if admin and task:
        db.add(Notification(
            user_id=admin.id,
            message=f"Volunteer rejected task: {task.title}",
            type="status_update",
        ))
    return {"status": "rejected"}


# ── Complete Assignment ───────────────────────────────────────────────────────

@router.post("/assignments/{assignment_id}/complete")
async def complete_assignment(
    assignment_id: str,
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    a = (await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.volunteer_id == user.user_id,
            Assignment.ngo_id == user.ngo_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if a.status != "accepted":
        raise HTTPException(status_code=400, detail=f"Cannot complete — current status: {a.status}")

    a.status = "completed"

    task = await db.get(Task, a.task_id)
    task_completed = False

    if task:
        active_remaining = (await db.execute(
            select(func.count()).select_from(Assignment).where(
                Assignment.task_id == a.task_id,
                Assignment.status.in_(["assigned", "accepted"]),
            )
        )).scalar() or 0
        if active_remaining == 0:
            task.status = "completed"
            task_completed = True

        admin = (await db.execute(
            select(User).where(User.ngo_id == user.ngo_id, User.role == "ngo_admin")
        )).scalar_one_or_none()
        if admin:
            db.add(Notification(
                user_id=admin.id,
                message=f"Volunteer {user.email} completed: {task.title}",
                type="status_update",
            ))

    return {"status": "completed", "task_completed": task_completed}


# ── Recommendations ───────────────────────────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    profile = (await db.execute(
        select(VolunteerProfile).where(VolunteerProfile.user_id == user.user_id)
    )).scalar_one_or_none()

    vol_skills = {s.lower() for s in (profile.skills or [])} if profile else set()

    open_tasks = (await db.execute(
        select(Task).where(Task.ngo_id == user.ngo_id, Task.status == "open")
    )).scalars().all()

    results = []
    for t in open_tasks:
        required = t.required_skills or []
        matched = [s for s in required if s.lower() in vol_skills]
        score = len(matched) / max(len(required), 1)
        results.append({
            "task_id":         t.id,
            "title":           t.title,
            "description":     t.description,
            "required_skills": required,
            "deadline":        t.deadline,
            "priority":        t.priority,
            "match_score":     round(score, 3),
            "matched_skills":  matched,
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:5]


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Notification)
        .where(Notification.user_id == user.user_id)
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .limit(50)
    )).scalars().all()
    return [
        {"id": n.id, "message": n.message, "type": n.type, "is_read": n.is_read, "created_at": n.created_at}
        for n in rows
    ]


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    user: CurrentUser = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
):
    n = (await db.execute(
        select(Notification).where(Notification.id == notif_id, Notification.user_id == user.user_id)
    )).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    return {"message": "Marked as read"}
