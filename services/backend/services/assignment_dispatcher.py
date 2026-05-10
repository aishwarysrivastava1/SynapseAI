from __future__ import annotations

import logging

from asgiref.sync import sync_to_async

from services.neo4j_service import neo4j_service
from services.realtime_events import realtime_bus

logger = logging.getLogger(__name__)


@sync_to_async
def _get_open_tasks(ngo_id: str) -> list:
    from apps.ngo.models import Task
    return list(Task.objects.filter(ngo_id=ngo_id, status="open"))


@sync_to_async
def _get_active_volunteers(ngo_id: str) -> list:
    from apps.accounts.models import User, VolunteerProfile
    profiles = list(VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active"))
    # Bulk-fetch matching users — O(1) queries instead of O(N)
    user_map = {u.id: u for u in User.objects.filter(id__in=[p.user_id for p in profiles])}
    return [(user_map[p.user_id], p) for p in profiles if p.user_id in user_map]


@sync_to_async
def _check_existing_assignment(task_id: str) -> bool:
    from apps.ngo.models import Assignment
    return Assignment.objects.filter(
        task_id=task_id, status__in=["assigned", "accepted"]
    ).exists()


@sync_to_async
def _create_assignment(task_id: str, volunteer_id: str, ngo_id: str, match_score: float) -> object:
    from apps.ngo.models import Assignment, Notification, Task
    a = Assignment.objects.create(
        task_id=task_id, volunteer_id=volunteer_id, ngo_id=ngo_id,
        status="assigned", match_score=match_score,
    )
    Task.objects.filter(id=task_id).update(status="in_progress")
    Notification.objects.create(
        user_id=volunteer_id,
        message=f"You have been assigned a new task",
        type="task_assigned",
    )
    return a


async def dispatch_optimized_assignments(
    *,
    ngo_id: str,
    max_assignments: int | None = None,
) -> list[dict]:
    from services.assignment_optimizer import optimize_task_assignments

    tasks = await _get_open_tasks(ngo_id)
    volunteers_data = await _get_active_volunteers(ngo_id)

    if not tasks or not volunteers_data:
        return []

    matches = await optimize_task_assignments(
        ngo_id=ngo_id,
        tasks=tasks,
        volunteers_data=volunteers_data,
        max_assignments=max_assignments,
    )
    if not matches:
        return []

    created: list[dict] = []
    for m in matches:
        if await _check_existing_assignment(m["task_id"]):
            continue

        a = await _create_assignment(m["task_id"], m["volunteer_id"], ngo_id, m["match_score"])

        try:
            await neo4j_service.upsert_assignment_edge(
                volunteer_id=m["volunteer_id"],
                task_id=m["task_id"],
                assignment_id=a.id,
            )
        except Exception as e:
            logger.warning("Neo4j upsert_assignment_edge failed for assignment %s: %s", a.id, e)

        await realtime_bus.publish(ngo_id, "assignment_updated", {
            "assignment_id": a.id,
            "task_id": m["task_id"],
            "volunteer_id": m["volunteer_id"],
            "status": a.status,
            "match_score": m["match_score"],
        })

        created.append({
            "assignment_id": a.id,
            "task_id": m["task_id"],
            "volunteer_id": m["volunteer_id"],
            "match_score": m["match_score"],
        })

    return created
