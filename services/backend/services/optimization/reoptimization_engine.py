from __future__ import annotations

from dataclasses import dataclass
from asgiref.sync import sync_to_async

from services.geo_routing_service import geo_routing_service
from .cost_function import INFEASIBLE_COST, OptimizationWeights
from .cost_matrix_builder import build_cost_matrix
from .greedy_solver import solve as greedy_solve
from .hungarian_solver import solve as hungarian_solve
from .route_optimizer import RouteOptimizationPlan, should_use_hungarian
from .types import AssignmentMatch, TaskSnapshot, VolunteerSnapshot


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    matches: list[AssignmentMatch]
    solver_used: str


@sync_to_async
def _load_workloads(ngo_id: str) -> dict[str, int]:
    from apps.ngo.models import Assignment
    from django.db.models import Count
    qs = (
        Assignment.objects.filter(ngo_id=ngo_id, status__in=["assigned","accepted"])
        .values("volunteer_id")
        .annotate(cnt=Count("id"))
    )
    return {r["volunteer_id"]: r["cnt"] for r in qs}


@sync_to_async
def _load_candidates_sync(ngo_id: str, tasks_override=None, volunteers_override=None):
    """
    Load tasks and volunteers from Django ORM.
    performance_score is computed from real assignment history (not left as None).
    """
    from apps.ngo.models import Task, Assignment
    from apps.accounts.models import User, VolunteerProfile
    from django.db.models import Avg, Count

    if tasks_override is not None:
        task_rows = tasks_override
    else:
        task_rows = list(Task.objects.filter(ngo_id=ngo_id, status="open").order_by("-urgency_score"))

    if volunteers_override is not None:
        vol_pairs = volunteers_override
    else:
        profiles = list(VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active"))
        user_map = {u.id: u for u in User.objects.filter(id__in=[p.user_id for p in profiles])}
        vol_pairs = [(user_map[p.user_id], p) for p in profiles if p.user_id in user_map]

    # Active workload (current assigned/accepted tasks)
    workload_qs = (
        Assignment.objects.filter(ngo_id=ngo_id, status__in=["assigned", "accepted"])
        .values("volunteer_id").annotate(cnt=Count("id"))
    )
    workloads = {r["volunteer_id"]: r["cnt"] for r in workload_qs}

    # Performance scores from completed assignment history
    # Formula: (avg_rating/5)*60 + avg_match_score*30 + min(count,10)*1  → 0..100
    vol_ids = [u.id for u, _ in vol_pairs]
    perf_qs = (
        Assignment.objects.filter(
            ngo_id=ngo_id, volunteer_id__in=vol_ids, status="completed"
        )
        .values("volunteer_id")
        .annotate(
            avg_rating=Avg("completion_rating"),
            avg_match=Avg("match_score"),
            completed=Count("id"),
        )
    )
    perf_map: dict[str, float] = {}
    for r in perf_qs:
        rating_score  = (float(r["avg_rating"] or 3.0) / 5.0) * 60.0
        match_score   = float(r["avg_match"]  or 0.7)  * 30.0
        exp_score     = min(int(r["completed"] or 0), 10) * 1.0
        perf_map[r["volunteer_id"]] = min(100.0, rating_score + match_score + exp_score)

    tasks = [
        TaskSnapshot(
            task_id=t.id, lat=t.lat, lng=t.lng,
            required_skills=tuple(t.required_skills or []),
            priority=t.priority,
            urgency_score=float(t.urgency_score) if t.urgency_score is not None else None,
            created_at=t.created_at,
        )
        for t in task_rows
    ]
    volunteers = [
        VolunteerSnapshot(
            volunteer_id=user.id, lat=profile.lat, lng=profile.lng,
            skills=tuple(profile.skills or []),
            availability=dict(profile.availability or {}),
            performance_score=perf_map.get(user.id),  # None → default in cost fn
            workload=workloads.get(user.id, 0),
        )
        for user, profile in vol_pairs
    ]
    return tasks, volunteers


async def optimize_task_assignments(
    ngo_id: str,
    tasks=None,
    volunteers_data=None,
    *,
    max_assignments: int | None = None,
    weights: OptimizationWeights = OptimizationWeights(),
    route_plan: RouteOptimizationPlan = RouteOptimizationPlan(),
) -> list[dict]:
    tasks_snap, volunteers_snap = await _load_candidates_sync(ngo_id, tasks, volunteers_data)
    if not tasks_snap or not volunteers_snap:
        return []

    matrix = await build_cost_matrix(
        volunteers_snap, tasks_snap,
        route_service=geo_routing_service,
        weights=weights, plan=route_plan,
    )
    if not matrix.cost_matrix:
        return []

    solver_used = "hungarian" if should_use_hungarian(len(volunteers_snap), len(tasks_snap), route_plan) else "greedy"
    try:
        pairs = hungarian_solve(matrix.cost_matrix) if solver_used == "hungarian" else greedy_solve(matrix.cost_matrix)
    except Exception:
        solver_used = "greedy"
        pairs = greedy_solve(matrix.cost_matrix)

    matches: list[AssignmentMatch] = []
    for row_index, col_index in pairs:
        score = matrix.score_matrix[row_index][col_index]
        if score.cost >= INFEASIBLE_COST:
            continue
        volunteer = volunteers_snap[matrix.volunteer_order[row_index]]
        task = tasks_snap[matrix.task_order[col_index]]
        matches.append(AssignmentMatch(
            volunteer_id=volunteer.volunteer_id, task_id=task.task_id,
            match_score=round(score.utility * 100.0, 2),
            cost=score.cost, distance_km=round(score.distance_km, 3),
            solver=solver_used,
        ))

    matches.sort(key=lambda m: m.match_score, reverse=True)
    if max_assignments:
        matches = matches[:max_assignments]

    return [{"volunteer_id": m.volunteer_id, "task_id": m.task_id, "match_score": m.match_score}
            for m in matches]
