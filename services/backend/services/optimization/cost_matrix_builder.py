"""
Cost matrix builder with Redis-backed distance cache.
Cache key is derived from sorted volunteer/task coordinate fingerprints.
TTL: 1 hour (distance data doesn't change often between runs).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

from .clustering import chunk_indices, task_order, volunteer_order
from .cost_function import OptimizationScore, OptimizationWeights, compute_pair_score
from .route_optimizer import RouteOptimizationPlan, should_batch_routes
from .types import MatrixBuildResult, TaskSnapshot, VolunteerSnapshot

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = int(os.getenv("DISTANCE_CACHE_TTL_S", 3600))


def _matrix_cache_key(
    volunteers: list[VolunteerSnapshot],
    tasks: list[TaskSnapshot],
) -> str:
    """Stable cache key based on coordinates, insensitive to list order."""
    vol_sig  = sorted((v.lat, v.lng) for v in volunteers if v.lat and v.lng)
    task_sig = sorted((t.lat, t.lng) for t in tasks       if t.lat and t.lng)
    raw = json.dumps({"v": vol_sig, "t": task_sig}, sort_keys=True)
    return "distmat:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _get_redis():
    """Lazy Redis import so module loads even if Redis is unavailable."""
    try:
        import redis.asyncio as aioredis
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        return aioredis.from_url(url, decode_responses=True)
    except Exception:
        return None


async def _cache_get(key: str) -> dict | None:
    r = await _get_redis()
    if not r:
        return None
    try:
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("Distance cache GET failed: %s", exc)
        return None


async def _cache_set(key: str, data: dict) -> None:
    r = await _get_redis()
    if not r:
        return
    try:
        await r.setex(key, _CACHE_TTL_SECONDS, json.dumps(data))
    except Exception as exc:
        logger.debug("Distance cache SET failed: %s", exc)


async def build_cost_matrix(
    volunteers: list[VolunteerSnapshot],
    tasks: list[TaskSnapshot],
    *,
    route_service,
    weights: OptimizationWeights = OptimizationWeights(),
    plan: RouteOptimizationPlan = RouteOptimizationPlan(),
) -> MatrixBuildResult:
    if not volunteers or not tasks:
        return MatrixBuildResult([], [], [], [], [])

    ordered_volunteers = volunteer_order(volunteers)
    ordered_tasks      = task_order(tasks)
    ordered_vol_snaps  = [volunteers[i] for i in ordered_volunteers]
    ordered_task_snaps = [tasks[i]      for i in ordered_tasks]

    # ── Distance matrix — Redis cache first ──────────────────────────────────
    cache_key = _matrix_cache_key(ordered_vol_snaps, ordered_task_snaps)
    cached = await _cache_get(cache_key)

    distance_lookup: dict[tuple[int, int], dict[str, float]]

    if cached:
        logger.debug("Distance matrix cache HIT (%s)", cache_key)
        # Deserialise: JSON keys are strings "row,col"
        distance_lookup = {
            (int(k.split(",")[0]), int(k.split(",")[1])): v
            for k, v in cached.items()
        }
    else:
        logger.debug("Distance matrix cache MISS — fetching from routing service")
        distance_lookup = {}

        if should_batch_routes(len(ordered_vol_snaps), len(ordered_task_snaps), plan):
            vol_batches  = chunk_indices(list(range(len(ordered_vol_snaps))),  plan.batch_size)
            task_batches = chunk_indices(list(range(len(ordered_task_snaps))), plan.batch_size)
            for vol_batch in vol_batches:
                origins = [
                    (ordered_vol_snaps[i].lat, ordered_vol_snaps[i].lng)
                    for i in vol_batch
                ]
                for task_batch in task_batches:
                    dests = [
                        (ordered_task_snaps[i].lat, ordered_task_snaps[i].lng)
                        for i in task_batch
                    ]
                    batch = await route_service.get_distance_matrix(origins, dests)
                    for local_row, vi in enumerate(vol_batch):
                        for local_col, ti in enumerate(task_batch):
                            distance_lookup[(vi, ti)] = batch.get(
                                (local_row, local_col),
                                {"distance_km": 9999.0, "duration_s": 999999.0},
                            )
        else:
            origins = [(s.lat, s.lng) for s in ordered_vol_snaps]
            dests   = [(s.lat, s.lng) for s in ordered_task_snaps]
            distance_lookup = await route_service.get_distance_matrix(origins, dests)

        # Persist to Redis with string keys for JSON serialisability
        serialisable = {f"{k[0]},{k[1]}": v for k, v in distance_lookup.items()}
        await _cache_set(cache_key, serialisable)

    # ── Build cost / score matrices ───────────────────────────────────────────
    cost_matrix:     list[list[float]]             = []
    distance_matrix: list[list[float]]             = []
    score_matrix:    list[list[OptimizationScore]] = []

    for vi, volunteer in enumerate(ordered_vol_snaps):
        cost_row, dist_row, score_row = [], [], []
        for ti, task in enumerate(ordered_task_snaps):
            cell  = distance_lookup.get((vi, ti), {"distance_km": 9999.0})
            dist  = float(cell.get("distance_km") or 9999.0)
            score = compute_pair_score(volunteer, task, dist, weights)
            cost_row.append(score.cost)
            dist_row.append(score.distance_km)
            score_row.append(score)
        cost_matrix.append(cost_row)
        distance_matrix.append(dist_row)
        score_matrix.append(score_row)

    return MatrixBuildResult(
        cost_matrix=cost_matrix,
        distance_matrix=distance_matrix,
        score_matrix=score_matrix,
        volunteer_order=ordered_volunteers,
        task_order=ordered_tasks,
    )
