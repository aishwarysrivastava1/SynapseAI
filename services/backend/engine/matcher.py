import numpy as np
from scipy.optimize import linear_sum_assignment
from services.neo4j_service import neo4j_service
import logging

logger = logging.getLogger(__name__)

async def compute_optimal_matches() -> dict:
    """Uses Hungarian Algorithm to match available volunteers to open tasks.
    
    Edge cases handled:
    - Empty volunteer list → returns empty matches
    - Empty task list → returns empty matches
    - More tasks than volunteers (or vice versa) → handled natively by linear_sum_assignment
    """
    try:
        # 1. Fetch data
        vols = await neo4j_service.run_query(
            "MATCH (v:Volunteer {availability_status: 'ACTIVE'}) RETURN v"
        )
        tasks = await neo4j_service.run_query(
            "MATCH (t:Task {status: 'OPEN'}) RETURN t"
        )
        
        vol_data = [v["v"] for v in vols] if vols else []
        task_data = [t["t"] for t in tasks] if tasks else []
        
        if not vol_data or not task_data:
            return {"matches": [], "message": "No active volunteers or open tasks to match"}
            
        n_vols = len(vol_data)
        n_tasks = len(task_data)
        
        # 2. Build cost matrix (rows=vols, cols=tasks)
        # Cost = lower is better
        cost_matrix = np.zeros((n_vols, n_tasks))
        
        for i, v in enumerate(vol_data):
            for j, t in enumerate(task_data):
                # Base cost
                cost = 100.0
                
                # Reputation bonus (higher rep = lower cost)
                rep = v.get("reputation_score", 50)
                if isinstance(rep, (int, float)):
                    cost -= rep * 0.2
                
                # (In a real app, calculate actual geospatial distance here)
                # distance = calc_distance(v_lat, v_lng, t_lat, t_lng)
                # cost += distance * 0.5
                
                cost_matrix[i][j] = max(cost, 0.0)  # No negative costs
                
        # 3. Hungarian Algorithm — handles rectangular matrices natively
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        matches = []
        for i, j in zip(row_ind, col_ind):
            matches.append({
                "volunteer_id": vol_data[i].get("id", f"vol_{i}"),
                "volunteer_name": vol_data[i].get("name", "Unknown"),
                "task_id": task_data[j].get("id", f"task_{j}"),
                "task_title": task_data[j].get("title", "Untitled"),
                "match_score": round(100 - cost_matrix[i][j], 1)
            })
            
        return {"matches": matches}
        
    except Exception as e:
        logger.error(f"Matching computation failed: {e}")
        return {"matches": [], "error": str(e)}
