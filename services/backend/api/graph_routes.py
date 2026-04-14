import pydantic
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any
from services.neo4j_service import neo4j_service
from services.langchain_cypher import text_to_cypher
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/needs")
async def get_needs(status: Optional[str] = None, type: Optional[str] = None, limit: int = Query(50)):
    match_clause = "MATCH (n:Need)-[:LOCATED_IN]->(l:Location)"
    where_clauses = []
    params = {"limit": limit}
    
    if status:
        where_clauses.append("n.status = $status")
        params["status"] = status
    if type:
        where_clauses.append("n.type = $type")
        params["type"] = type
        
    where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    cypher = f"{match_clause}{where_str} RETURN n, l ORDER BY n.urgency_score DESC LIMIT $limit"
    
    try:
        results = await neo4j_service.run_query(cypher, params)
        return {"needs": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error executing query.")

@router.get("/needs/{need_id}")
async def get_need(need_id: str):
    try:
        cypher = """
        MATCH (n:Need {id: $need_id})
        OPTIONAL MATCH (n)-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (n)-[:REQUIRES_SKILL]->(s:Skill)
        OPTIONAL MATCH (n)-[:SPAWNED_TASK]->(t:Task)
        RETURN n, l, collect(s) as skills, collect(t) as tasks
        """
        results = await neo4j_service.run_query(cypher, {"need_id": need_id})
        if not results:
            raise HTTPException(status_code=404, detail="Need not found")
        return results[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/volunteers")
async def get_volunteers():
    try:
        cypher = """
        MATCH (v:Volunteer)
        OPTIONAL MATCH (v)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (v)-[:LOCATED_IN]->(l:Location)
        RETURN v, collect(s) as skills, l
        """
        return {"volunteers": await neo4j_service.run_query(cypher)}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

# Field whitelisting to prevent Mass Assignment / IDOR
ALLOWED_MODELS = {
    "Need": ["status", "urgency_score"],
    "Volunteer": ["availabilityStatus", "reputation_score"],
    "Task": ["status"]
}

class NodeUpdateReq(pydantic.BaseModel):
    nodeType: str
    nodeId: str
    updates: Dict[str, Any]

@router.post("/update-node")
async def update_node(req: NodeUpdateReq):
    node_type = req.nodeType
    node_id = req.nodeId
    updates = req.updates
    
    if not node_type or not node_id or not updates:
        raise HTTPException(status_code=400, detail="Missing required fields")
        
    if node_type not in ALLOWED_MODELS:
        raise HTTPException(status_code=403, detail="Invalid node type for updates")
        
    # Sanitize inputs via whitelist checks
    sanitized_updates = {k: v for k, v in updates.items() if k in ALLOWED_MODELS[node_type]}
    if not sanitized_updates:
        raise HTTPException(status_code=400, detail="No allowable fields provided for update")
        
    # SAFETY: node_type is validated against ALLOWED_MODELS above (line 76).
    # Neo4j does not support parameterized labels, so f-string is required here.
    # Field keys are also constrained by the whitelist — no injection vector.
    set_clause = ", ".join([f"n.{k} = ${k}" for k in sanitized_updates.keys()])
    cypher = f"MATCH (n:{node_type} {{id: $id}}) SET {set_clause} RETURN n"
    params = sanitized_updates.copy()
    params["id"] = node_id
    
    try:
        results = await neo4j_service.run_query(cypher, params)
        return {"success": True, "updated": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database operation failed")

class AskReq(pydantic.BaseModel):
    query: str

@router.post("/ask")
async def ask_graph(req: AskReq):
    try:
        result = await text_to_cypher(req.query)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to parse query safely")

@router.get("/hotspots")
async def get_hotspots():
    """Identifies high-need areas by clustering unresolved community requirements."""
    try:
        cypher = """
        MATCH (n:Need {status: 'PENDING'})-[:LOCATED_IN]->(l:Location)
        RETURN l.name as area, count(n) as need_count, collect(n.description)[0..3] as sample_needs
        ORDER BY need_count DESC
        """
        results = await neo4j_service.run_query(cypher)
        return {"hotspots": results}
    except Exception as e:
        logger.error(f"Failed to fetch hotspots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching hotspots")


