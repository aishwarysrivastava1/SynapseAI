from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from engine.simulator import run_simulation_scenario, run_comparison_scenario
from engine.matcher import compute_optimal_matches, perform_auto_assignment
from middleware.rbac import get_current_user, CurrentUser
from utils.errors import safe_http_error
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SimRunReq(BaseModel):
    strategy: Optional[str] = "skill_first"
    num_steps: Optional[int] = 50

class CompareReq(BaseModel):
    num_steps: Optional[int] = 100

@router.post("/run")
async def run_sim(req: SimRunReq = None, user: CurrentUser = Depends(get_current_user)):
    """Run a single simulation scenario with the given strategy."""
    strategy = (req.strategy if req else "skill_first")
    steps = (req.num_steps if req else 50)
    strategy = strategy if strategy in ("skill_first", "proximity_first", "random") else "skill_first"
    steps = max(10, min(steps, 200))
    try:
        return await run_simulation_scenario(num_steps=steps, strategy=strategy)
    except Exception as e:
        raise safe_http_error(500, "Simulation service unavailable", e, "run_sim")

@router.post("/compare")
async def compare_strategies(req: CompareReq = None, user: CurrentUser = Depends(get_current_user)):
    """Compare skill_first vs proximity_first vs random strategies side-by-side."""
    steps = (req.num_steps if req else 100)
    steps = max(10, min(steps, 200))
    try:
        return await run_comparison_scenario(steps=steps)
    except Exception as e:
        raise safe_http_error(500, "Simulation service unavailable", e, "compare_strategies")

@router.post("/match/run")
async def run_matching(user: CurrentUser = Depends(get_current_user)):
    """Execute the Hungarian algorithm matcher and commit assignments to Neo4j + Firestore."""
    try:
        await perform_auto_assignment()
        result = await compute_optimal_matches()
        return {"success": True, "assignments": result.get("matches", []),
                "total": len(result.get("matches", []))}
    except Exception as e:
        raise safe_http_error(500, "Matching service unavailable", e, "run_matching")

@router.get("/match/assignments")
async def get_assignments(user: CurrentUser = Depends(get_current_user)):
    """Return current volunteer-to-need assignments from Neo4j."""
    try:
        return await compute_optimal_matches()
    except Exception as e:
        logger.error(f"Get assignments failed: {e}")
        raise HTTPException(status_code=500, detail="Matching computation failed")
