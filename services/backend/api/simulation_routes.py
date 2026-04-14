from fastapi import APIRouter, HTTPException, Query
from engine.simulator import run_simulation_scenario, run_comparison_scenario
from engine.matcher import compute_optimal_matches

router = APIRouter()

@router.get("/run")
async def run_sim(steps: int = Query(50, ge=1, le=500), strategy: str = "random"):
    try:
        return await run_simulation_scenario(num_steps=steps, strategy=strategy)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Simulation failed")

@router.get("/matches")
async def get_matches():
    try:
        return await compute_optimal_matches()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Matching computation failed")

@router.post("/compare")
async def compare_strategies(steps: int = Query(100, ge=1, le=500)):
    """Compares different dispatch strategies to optimize community outcome."""
    try:
        return await run_comparison_scenario(steps=steps)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Comparison simulation failed")
