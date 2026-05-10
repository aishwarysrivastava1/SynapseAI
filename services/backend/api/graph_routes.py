"""
Knowledge Graph API — fully multi-tenant (all queries scoped to user.ngo_id).
"""
from __future__ import annotations

import logging
import os
import secrets as _secrets
from typing import Optional

import pydantic
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from middleware.rbac import CurrentUser, get_current_user
from services.neo4j_service import neo4j_service
from services.langchain_cypher import text_to_cypher

logger = logging.getLogger(__name__)

INTERNAL_SERVICE_SECRET = os.environ.get("INTERNAL_SERVICE_SECRET", "")

router = APIRouter()

ALLOWED_UPDATE_MODELS = {
    "Need":      ["status", "urgency_score"],
    "Volunteer": ["availabilityStatus", "reputationScore"],
    "Task":      ["status"],
}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(user: CurrentUser = Depends(get_current_user)):
    """Dashboard KPIs scoped to the requesting NGO."""
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {ngo_id: $ngo_id})
        WITH
            count(n) AS total_needs,
            count(CASE WHEN n.status = 'PENDING'  THEN 1 END) AS pending_needs,
            count(CASE WHEN n.status = 'CLAIMED'  THEN 1 END) AS claimed_needs,
            count(CASE WHEN n.status = 'VERIFIED' THEN 1 END) AS verified_needs,
            count(CASE WHEN n.status IN ['CLAIMED','VERIFIED'] THEN 1 END) AS addressed_needs
        OPTIONAL MATCH (v:Volunteer {ngo_id: $ngo_id})
        WITH total_needs, pending_needs, claimed_needs, verified_needs, addressed_needs,
             count(v) AS total_volunteers
        OPTIONAL MATCH (v2:Volunteer {ngo_id: $ngo_id, availabilityStatus: 'ACTIVE'})
        RETURN
            total_needs, pending_needs, claimed_needs, verified_needs, total_volunteers,
            count(v2) AS active_volunteers,
            CASE WHEN total_needs > 0
                 THEN round(toFloat(addressed_needs) / total_needs * 100)
                 ELSE 0 END AS coverage_pct
        """
        results = await neo4j_service.run_query(cypher, {"ngo_id": ngo_id})
        if not results:
            return {"total_needs": 0, "pending_needs": 0, "claimed_needs": 0,
                    "verified_needs": 0, "total_volunteers": 0,
                    "active_volunteers": 0, "coverage_pct": 0}
        return results[0]
    except Exception as exc:
        logger.error("get_stats failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


# ── Needs ─────────────────────────────────────────────────────────────────────

@router.get("/needs")
async def get_needs(
    status: Optional[str] = None,
    type:   Optional[str] = None,
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    where_clauses = ["n.ngo_id = $ngo_id"]
    params: dict  = {"ngo_id": ngo_id, "limit": limit, "offset": offset}

    if status:
        where_clauses.append("n.status = $status")
        params["status"] = status
    if type:
        where_clauses.append("n.type = $type")
        params["type"] = type

    where_str = " WHERE " + " AND ".join(where_clauses)
    cypher = (
        f"MATCH (n:Need)-[:LOCATED_IN]->(l:Location){where_str} "
        "RETURN n, l ORDER BY n.urgency_score DESC SKIP $offset LIMIT $limit"
    )
    try:
        results = await neo4j_service.run_query(cypher, params)
        return {"needs": results, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.error("get_needs failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch needs")


@router.get("/needs/{need_id}")
async def get_need(need_id: str, user: CurrentUser = Depends(get_current_user)):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {id: $id, ngo_id: $ngo_id})-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (n)-[:REQUIRES_SKILL]->(s:Skill)
        RETURN n, l, collect(s) AS required_skills
        """
        results = await neo4j_service.run_query(cypher, {"id": need_id, "ngo_id": ngo_id})
        if not results:
            raise HTTPException(status_code=404, detail="Need not found")
        return results[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_need failed ngo=%s need=%s: %s", ngo_id, need_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch need")


# ── Volunteers ────────────────────────────────────────────────────────────────

@router.get("/volunteers")
async def get_volunteers(
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (v:Volunteer {ngo_id: $ngo_id})
        OPTIONAL MATCH (v)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (v)-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (v)-[:ASSIGNED_TO]->(n:Need)
        RETURN v, collect(DISTINCT s) AS skills, l, collect(DISTINCT n) AS assigned_needs
        SKIP $offset LIMIT $limit
        """
        return {
            "volunteers": await neo4j_service.run_query(
                cypher, {"ngo_id": ngo_id, "limit": limit, "offset": offset}
            ),
            "limit": limit, "offset": offset,
        }
    except Exception as exc:
        logger.error("get_volunteers failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch volunteers")


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def get_tasks(
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0,  ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (t:Task {ngo_id: $ngo_id})
        OPTIONAL MATCH (t)-[:LOCATED_IN]->(l:Location)
        RETURN t, l ORDER BY t.created_at DESC SKIP $offset LIMIT $limit
        """
        return {
            "tasks": await neo4j_service.run_query(
                cypher, {"ngo_id": ngo_id, "limit": limit, "offset": offset}
            ),
            "limit": limit, "offset": offset,
        }
    except Exception as exc:
        logger.error("get_tasks failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


# ── Causal Chain ──────────────────────────────────────────────────────────────

@router.get("/causal-chain")
async def get_causal_chain(
    limit:  int = Query(30, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (a:Need {ngo_id: $ngo_id})-[:CAUSED_BY]->(b:Need {ngo_id: $ngo_id})
        OPTIONAL MATCH (a)-[:LOCATED_IN]->(la:Location)
        OPTIONAL MATCH (b)-[:LOCATED_IN]->(lb:Location)
        RETURN a.id AS from_id, a.type AS from_type, a.urgency_score AS from_urgency,
               b.id AS to_id, b.type AS to_type, b.urgency_score AS to_urgency,
               la.name AS from_location, lb.name AS to_location
        LIMIT $limit
        """
        results = await neo4j_service.run_query(cypher, {"ngo_id": ngo_id, "limit": limit})
        return {"causal_edges": results, "count": len(results)}
    except Exception as exc:
        logger.error("get_causal_chain failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch causal chain")


# ── Graph Nodes (for visualization) ──────────────────────────────────────────

@router.get("/nodes")
async def get_all_nodes(
    limit:  int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    """Return graph nodes for force-directed visualization — NGO-scoped."""
    ngo_id = user.ngo_id
    try:
        needs = await neo4j_service.run_query(
            "MATCH (n:Need {ngo_id: $ngo_id}) "
            "RETURN n.id AS id, 'Need' AS label, n.type AS type, "
            "n.urgency_score AS urgency_score, n.status AS status, "
            "n.description AS description LIMIT $limit",
            {"ngo_id": ngo_id, "limit": limit},
        )
        volunteers = await neo4j_service.run_query(
            "MATCH (v:Volunteer {ngo_id: $ngo_id}) "
            "RETURN v.id AS id, 'Volunteer' AS label, v.name AS name, "
            "v.availabilityStatus AS status, coalesce(v.totalXP, 0) AS xp LIMIT $limit",
            {"ngo_id": ngo_id, "limit": limit},
        )
        locs = await neo4j_service.run_query(
            "MATCH (l:Location) "
            "RETURN l.id AS id, 'Location' AS label, l.name AS name, l.lat AS lat, l.lng AS lng LIMIT 20",
        )
        skills = await neo4j_service.run_query(
            "MATCH (s:Skill) "
            "RETURN s.name AS id, 'Skill' AS label, s.name AS name, s.category AS category LIMIT 20",
        )
        edges = await neo4j_service.run_query(
            """
            MATCH (a:Need {ngo_id: $ngo_id})-[r]->(b)
            WHERE a.id IS NOT NULL
            RETURN a.id AS source,
                   CASE WHEN b.id IS NOT NULL THEN b.id ELSE b.name END AS target,
                   type(r) AS relationship
            LIMIT 150
            """,
            {"ngo_id": ngo_id},
        )
        nodes = needs + volunteers + locs + skills
        return {"nodes": nodes, "edges": edges, "count": len(nodes)}
    except Exception as exc:
        logger.error("get_all_nodes failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch graph nodes")


# ── NLP → Cypher query ────────────────────────────────────────────────────────

class AskReq(pydantic.BaseModel):
    query: str = pydantic.Field(..., max_length=500)


@router.post("/ask")
async def ask_graph(req: AskReq, user: CurrentUser = Depends(get_current_user)):
    """
    Translate a natural-language question into a read-only Cypher query.
    The ngo_id is injected into the question context so the LLM scopes results.
    """
    ngo_id = user.ngo_id
    try:
        # Prepend NGO scope hint so LLM generates scoped queries
        scoped_query = f"{req.query} [ngo_id: {ngo_id}]"
        result = await text_to_cypher(scoped_query)
        if result.get("error"):
            return {"cypher": result.get("cypher"), "results": [], "error": result["error"]}
        return result
    except Exception as exc:
        logger.error("ask_graph failed ngo=%s: %s", ngo_id, exc)
        return {"cypher": None, "results": [], "error": "Failed to parse query safely"}


# ── Hotspots ──────────────────────────────────────────────────────────────────

@router.get("/hotspots")
async def get_hotspots(
    limit:  int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    ngo_id = user.ngo_id
    try:
        cypher = """
        MATCH (n:Need {ngo_id: $ngo_id, status: 'PENDING'})-[:LOCATED_IN]->(l:Location)
        RETURN l.name AS area, l.lat AS lat, l.lng AS lng,
               count(n) AS need_count,
               round(avg(n.urgency_score) * 100) / 100.0 AS avg_urgency,
               sum(n.population_affected) AS total_affected,
               collect(n.description)[0..3] AS sample_needs
        ORDER BY avg_urgency DESC LIMIT $limit
        """
        results = await neo4j_service.run_query(cypher, {"ngo_id": ngo_id, "limit": limit})
        return {"hotspots": results}
    except Exception as exc:
        logger.error("get_hotspots failed ngo=%s: %s", ngo_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch hotspots")


# ── Internal node update ──────────────────────────────────────────────────────

class NodeUpdateReq(pydantic.BaseModel):
    nodeType: str
    nodeId:   str
    updates:  dict


@router.post("/update-node")
async def update_node(
    req: NodeUpdateReq,
    x_service_secret: str = Header(default=""),
):
    if INTERNAL_SERVICE_SECRET and not _secrets.compare_digest(
        x_service_secret, INTERNAL_SERVICE_SECRET
    ):
        logger.warning("update-node: invalid secret for %s %s", req.nodeType, req.nodeId)
        raise HTTPException(status_code=401, detail="Unauthorized")

    if req.nodeType not in ALLOWED_UPDATE_MODELS:
        raise HTTPException(status_code=403, detail="Invalid node type")

    sanitized = {
        k: v for k, v in req.updates.items()
        if k in ALLOWED_UPDATE_MODELS[req.nodeType]
    }
    if not sanitized:
        raise HTTPException(status_code=400, detail="No allowable fields provided")

    set_clause = ", ".join(f"n.{k} = ${k}" for k in sanitized)
    cypher = f"MATCH (n:{req.nodeType} {{id: $id}}) SET {set_clause} RETURN n"
    params = {**sanitized, "id": req.nodeId}

    try:
        results = await neo4j_service.run_query(cypher, params)
        return {"success": True, "updated": results}
    except Exception as exc:
        logger.error("update_node failed: %s", exc)
        raise HTTPException(status_code=500, detail="Database operation failed")
