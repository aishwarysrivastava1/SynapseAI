"""
Analytics API — NGO-scoped. All queries filtered by user.ngo_id.
PostgreSQL used for operational metrics; Neo4j for graph analytics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Query

from middleware.rbac import CurrentUser, get_current_user
from services.firebase_service import firebase_service
from services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── PostgreSQL helpers ────────────────────────────────────────────────────────

@sync_to_async
def _pg_ngo_overview(ngo_id: str) -> dict:
    """Real operational metrics from PostgreSQL."""
    from django.db.models import Avg, Count
    from apps.accounts.models import VolunteerProfile
    from apps.ngo.models import Assignment, Task

    total_tasks = Task.objects.filter(ngo_id=ngo_id).count()
    open_tasks  = Task.objects.filter(ngo_id=ngo_id, status="open").count()
    in_progress = Task.objects.filter(ngo_id=ngo_id, status="in_progress").count()
    completed   = Task.objects.filter(ngo_id=ngo_id, status="completed").count()

    active_vols  = VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active").count()
    total_vols   = VolunteerProfile.objects.filter(ngo_id=ngo_id).count()

    total_assigns    = Assignment.objects.filter(ngo_id=ngo_id).count()
    completed_assigns = Assignment.objects.filter(ngo_id=ngo_id, status="completed").count()
    avg_match = (
        Assignment.objects.filter(ngo_id=ngo_id, match_score__isnull=False)
        .aggregate(v=Avg("match_score"))["v"] or 0.0
    )

    completion_rate = round(completed / max(total_tasks, 1) * 100, 1)
    utilization     = round(active_vols / max(total_vols, 1) * 100, 1)

    return {
        "tasks": {
            "total": total_tasks, "open": open_tasks,
            "in_progress": in_progress, "completed": completed,
            "completion_rate_pct": completion_rate,
        },
        "volunteers": {
            "total": total_vols, "active": active_vols,
            "utilization_pct": utilization,
        },
        "assignments": {
            "total": total_assigns, "completed": completed_assigns,
            "avg_match_score": round(float(avg_match), 3),
        },
    }


@sync_to_async
def _pg_skill_gaps(ngo_id: str) -> list:
    """Compare skill supply (volunteers) vs demand (open tasks) from PostgreSQL."""
    from collections import Counter
    from apps.accounts.models import VolunteerProfile
    from apps.ngo.models import Task

    supply: Counter = Counter()
    for p in VolunteerProfile.objects.filter(ngo_id=ngo_id, status="active").only("skills"):
        for s in (p.skills or []):
            supply[s.lower()] += 1

    demand: Counter = Counter()
    for t in Task.objects.filter(ngo_id=ngo_id, status__in=["open", "in_progress"]).only("required_skills"):
        for s in (t.required_skills or []):
            demand[s.lower()] += 1

    result = []
    for skill, dem in sorted(demand.items(), key=lambda x: -x[1]):
        sup = supply.get(skill, 0)
        result.append({
            "skill":  skill,
            "demand": dem,
            "supply": sup,
            "gap":    max(0, dem - sup),
        })
    return result[:20]


@sync_to_async
def _pg_volunteer_leaderboard(ngo_id: str, limit: int = 10) -> list:
    """Top volunteers by completed tasks + avg match score from PostgreSQL."""
    from django.db.models import Avg, Count
    from apps.accounts.models import User, VolunteerProfile
    from apps.ngo.models import Assignment

    rows = (
        Assignment.objects.filter(ngo_id=ngo_id, status="completed")
        .values("volunteer_id")
        .annotate(
            completed_count=Count("id"),
            avg_score=Avg("match_score"),
            avg_rating=Avg("completion_rating"),
        )
        .order_by("-completed_count")[:limit]
    )

    user_ids = [r["volunteer_id"] for r in rows]
    profiles = {
        p.user_id: p for p in VolunteerProfile.objects.filter(user_id__in=user_ids)
    }
    users = {u.id: u for u in User.objects.filter(id__in=user_ids)}

    leaderboard = []
    for i, r in enumerate(rows, 1):
        vid  = r["volunteer_id"]
        prof = profiles.get(vid)
        usr  = users.get(vid)
        leaderboard.append({
            "rank":            i,
            "volunteer_id":    vid,
            "name":            (prof.full_name if prof else None) or (usr.email.split("@")[0] if usr else vid),
            "completed_tasks": r["completed_count"],
            "avg_match_score": round(float(r["avg_score"] or 0), 3),
            "avg_rating":      round(float(r["avg_rating"] or 0), 2),
        })
    return leaderboard


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/ngo-overview")
async def ngo_overview(user: CurrentUser = Depends(get_current_user)):
    """
    Real-time operational dashboard metrics from PostgreSQL.
    Use this as the primary analytics source for NGO dashboards.
    """
    try:
        return await _pg_ngo_overview(user.ngo_id)
    except Exception as exc:
        logger.error("ngo_overview failed for ngo=%s: %s", user.ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch NGO overview")


@router.get("/skill-gaps")
async def skill_gaps(user: CurrentUser = Depends(get_current_user)):
    """PostgreSQL-backed skill supply/demand gap analysis."""
    try:
        return {"gaps": await _pg_skill_gaps(user.ngo_id)}
    except Exception as exc:
        logger.error("skill_gaps failed for ngo=%s: %s", user.ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch skill gaps")


@router.get("/leaderboard")
async def volunteer_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    """Top volunteers by completed task count + match quality from PostgreSQL."""
    try:
        return {"leaderboard": await _pg_volunteer_leaderboard(user.ngo_id, limit)}
    except Exception as exc:
        logger.error("leaderboard failed for ngo=%s: %s", user.ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")


@router.get("/summary")
async def get_summary(user: CurrentUser = Depends(get_current_user)):
    """Neo4j graph summary scoped to the requesting NGO."""
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {ngo_id: $ngo_id})
        WITH
            count(n)                                                AS total_needs,
            count(CASE WHEN n.status = 'PENDING'  THEN 1 END)      AS pending,
            count(CASE WHEN n.status IN ['CLAIMED','VERIFIED'] THEN 1 END) AS resolved,
            avg(n.urgency_score)                                    AS avg_urgency,
            sum(n.population_affected)                              AS total_affected
        OPTIONAL MATCH (v:Volunteer {ngo_id: $ngo_id})
        WITH total_needs, pending, resolved, avg_urgency, total_affected,
             count(v) AS total_volunteers
        OPTIONAL MATCH (v2:Volunteer {ngo_id: $ngo_id, availabilityStatus: 'ACTIVE'})
        RETURN
            total_needs,
            pending,
            resolved,
            round(coalesce(avg_urgency, 0) * 100) / 100.0 AS avg_urgency,
            coalesce(total_affected, 0)                   AS total_affected,
            total_volunteers,
            count(v2) AS active_volunteers
        """
        results = await neo4j_service.run_query(cypher, {"ngo_id": ngo_id})
        if not results:
            return {"total_needs": 0, "pending": 0, "resolved": 0,
                    "avg_urgency": 0, "total_affected": 0,
                    "total_volunteers": 0, "active_volunteers": 0}
        return results[0]
    except Exception as exc:
        logger.error("summary failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")


@router.get("/needs-by-type")
async def get_needs_by_type(
    limit:  int = Query(20, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = (
            "MATCH (n:Need {ngo_id: $ngo_id}) "
            "RETURN n.type AS type, count(n) AS count "
            "ORDER BY count DESC SKIP $offset LIMIT $limit"
        )
        results = await neo4j_service.run_query(
            cypher, {"ngo_id": ngo_id, "limit": limit, "offset": offset}
        )
        return {"data": results, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.error("needs-by-type failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch needs by type")


@router.get("/urgency-distribution")
async def get_urgency_distribution(user: CurrentUser = Depends(get_current_user)):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {ngo_id: $ngo_id})
        RETURN
            count(CASE WHEN n.urgency_score < 0.3  THEN 1 END)                               AS low,
            count(CASE WHEN n.urgency_score >= 0.3 AND n.urgency_score < 0.6 THEN 1 END)     AS medium,
            count(CASE WHEN n.urgency_score >= 0.6 AND n.urgency_score < 0.8 THEN 1 END)     AS high,
            count(CASE WHEN n.urgency_score >= 0.8 THEN 1 END)                               AS critical
        """
        results = await neo4j_service.run_query(cypher, {"ngo_id": ngo_id})
        return results[0] if results else {"low": 0, "medium": 0, "high": 0, "critical": 0}
    except Exception as exc:
        logger.error("urgency-distribution failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch urgency distribution")


@router.get("/skill-coverage")
async def get_skill_coverage(user: CurrentUser = Depends(get_current_user)):
    """Neo4j graph-based skill coverage (demand vs supply within NGO)."""
    ngo_id = user.ngo_id
    try:
        demanded_cypher = """
        MATCH (n:Need {ngo_id: $ngo_id, status: 'PENDING'})-[:REQUIRES_SKILL]->(s:Skill)
        RETURN s.name AS skill, count(n) AS demand
        ORDER BY demand DESC LIMIT 20
        """
        supplied_cypher = """
        MATCH (v:Volunteer {ngo_id: $ngo_id, availabilityStatus: 'ACTIVE'})-[:HAS_SKILL]->(s:Skill)
        RETURN s.name AS skill, count(v) AS supply
        """
        demanded, supplied = (
            await neo4j_service.run_query(demanded_cypher, {"ngo_id": ngo_id}),
            await neo4j_service.run_query(supplied_cypher, {"ngo_id": ngo_id}),
        )
        supply_map = {r["skill"]: r["supply"] for r in supplied}
        coverage = [
            {
                "skill":  r["skill"],
                "demand": r["demand"],
                "supply": supply_map.get(r["skill"], 0),
                "gap":    max(0, r["demand"] - supply_map.get(r["skill"], 0)),
            }
            for r in demanded
        ]
        return {"coverage": coverage}
    except Exception as exc:
        logger.error("skill-coverage failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch skill coverage")


@router.get("/hotzone-ranking")
async def get_hotzone_ranking(
    limit:  int = Query(20, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {ngo_id: $ngo_id, status: 'PENDING'})-[:LOCATED_IN]->(l:Location)
        RETURN l.name AS zone, count(n) AS need_count,
               round(sum(n.urgency_score) * 100) / 100.0 AS total_urgency,
               sum(n.population_affected) AS total_affected
        ORDER BY total_urgency DESC SKIP $offset LIMIT $limit
        """
        results = await neo4j_service.run_query(
            cypher, {"ngo_id": ngo_id, "limit": limit, "offset": offset}
        )
        return {"hotzones": results, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.error("hotzone-ranking failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch hotzone ranking")


@router.get("/trend")
async def get_trend(
    days: int = Query(7, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user),
):
    """Need ingestion trend from Firestore activity log, scoped to NGO."""
    ngo_id = user.ngo_id
    try:
        trend: list = []
        if firebase_service.db:
            cutoff = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            events = (
                firebase_service.db
                .collection("activity")
                .where("type", "==", "NEED_REPORTED")
                .where("ngo_id", "==", ngo_id)
                .where("timestamp", ">=", cutoff)
                .order_by("timestamp")
                .stream()
            )
            counts: dict = {}
            for ev in events:
                d = ev.to_dict().get("timestamp")
                if d:
                    day_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
                    counts[day_str] = counts.get(day_str, 0) + 1
            now_naive = datetime.now(tz=timezone.utc).replace(tzinfo=None)
            for i in range(days):
                day = (now_naive - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
                trend.append({"date": day, "count": counts.get(day, 0)})
        else:
            return {"trend": [], "days": days, "data_unavailable": True}

        return {"trend": trend, "days": days}
    except Exception as exc:
        logger.error("trend failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch trend data")


@router.get("/volunteer-activity")
async def get_volunteer_activity(
    limit:  int = Query(20, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    """Top volunteers by tasks completed — Neo4j graph node data, NGO-scoped."""
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (v:Volunteer {ngo_id: $ngo_id})
        RETURN v.name AS name,
               coalesce(v.totalTasksCompleted, 0) AS tasks_completed,
               coalesce(v.totalXP, 0)             AS xp,
               coalesce(v.reputationScore, 0)      AS reputation
        ORDER BY tasks_completed DESC SKIP $offset LIMIT $limit
        """
        results = await neo4j_service.run_query(
            cypher, {"ngo_id": ngo_id, "limit": limit, "offset": offset}
        )
        return {"data": results, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.error("volunteer-activity failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch volunteer activity")


@router.get("/coverage-history")
async def get_coverage_history(user: CurrentUser = Depends(get_current_user)):
    """Simulation run history for this NGO from Firestore."""
    ngo_id = user.ngo_id
    try:
        history: list = []
        if firebase_service.db:
            runs = (
                firebase_service.db
                .collection("simulation_runs")
                .where("ngo_id", "==", ngo_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(10)
                .stream()
            )
            for r in runs:
                d = r.to_dict()
                history.append({
                    "run_id":       r.id,
                    "strategy":     d.get("strategy", "unknown"),
                    "coverage_pct": d.get("final_coverage", 0),
                    "timestamp":    str(d.get("timestamp", ""))[:10],
                })
        if not history:
            return {"history": [], "data_unavailable": True}
        return {"history": history}
    except Exception as exc:
        logger.error("coverage-history failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch coverage history")
