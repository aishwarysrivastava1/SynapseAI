import mesa
import logging
from services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)

class VolunteerAgent(mesa.Agent):
    def __init__(self, unique_id, model, speed=1, skills=None):
        super().__init__(unique_id, model)
        self.speed = speed
        self.skills = skills or []
        self.assigned_task = None
        self.tasks_completed = 0

    def step(self):
        if not self.assigned_task:
            return
            
        # Move towards task (simplified progress)
        self.assigned_task["progress"] += self.speed
        if self.assigned_task["progress"] >= self.assigned_task.get("difficulty", 10):
            self.tasks_completed += 1
            self.model.completed_tasks.append(self.assigned_task["id"])
            self.assigned_task = None

class NGOSimulation(mesa.Model):
    def __init__(self, volunteers_data, tasks_data, strategy="random"):
        super().__init__()
        self.schedule = mesa.time.RandomActivation(self)
        self.completed_tasks = []
        self.time_steps = 0
        self.tasks_data = tasks_data
        self.strategy = strategy
        
        for i, v_data in enumerate(volunteers_data):
            rep = v_data.get("reputation_score", 50)
            speed = rep / 50.0 if rep > 0 else 0.1
            agent = VolunteerAgent(i, self, speed=speed)
            self.schedule.add(agent)
            
        self.assign_tasks()
        
    def assign_tasks(self):
        available_agents = [a for a in self.schedule.agents if not a.assigned_task]
        pending_tasks = [t for t in self.tasks_data if t.get("id") not in self.completed_tasks]
        
        if self.strategy == "urgency":
            # Prioritize tasks with higher urgency scores
            pending_tasks = sorted(pending_tasks, key=lambda x: x.get("urgency_score", 0), reverse=True)
        
        for t in pending_tasks:
            if not available_agents:
                break
            t["progress"] = t.get("progress", 0)
            t["difficulty"] = t.get("difficulty", 10)
            agent = available_agents.pop(0)
            agent.assigned_task = t

    def step(self):
        self.schedule.step()
        self.assign_tasks()
        self.time_steps += 1
        
        if len(self.completed_tasks) >= len(self.tasks_data):
            self.running = False

async def get_sim_data():
    vol_cypher = "MATCH (v:Volunteer) RETURN v LIMIT 50"
    task_cypher = "MATCH (t:Task {status: 'OPEN'}) RETURN t LIMIT 50"
    
    vols = await neo4j_service.run_query(vol_cypher)
    tasks = await neo4j_service.run_query(task_cypher)
    
    vol_data = [v["v"] for v in vols] if vols else []
    task_data = [t["t"] for t in tasks] if tasks else []
    return vol_data, task_data

async def run_simulation_scenario(num_steps: int = 50, strategy: str = "random") -> dict:
    num_steps = min(num_steps, 500)
    vol_data, task_data = await get_sim_data()
    
    if not task_data:
        return {"message": "No open tasks to simulate", "tasks_completed": 0, "total_tasks": 0}
    if not vol_data:
        return {"message": "No volunteers available", "tasks_completed": 0, "total_tasks": len(task_data)}
        
    model = NGOSimulation(vol_data, [t.copy() for t in task_data], strategy=strategy)
    
    for i in range(num_steps):
        if not model.running:
            break
        model.step()
        
    return {
        "strategy": strategy,
        "steps_simulated": model.time_steps,
        "tasks_completed": len(model.completed_tasks),
        "total_tasks": len(task_data),
        "completion_rate": round(len(model.completed_tasks) / len(task_data) * 100, 1) if task_data else 0,
        "estimated_hours": round(model.time_steps * 0.5, 1)
    }

async def run_comparison_scenario(steps: int = 100) -> dict:
    """Runs parallel simulations to compare assignment strategies."""
    results_a = await run_simulation_scenario(num_steps=steps, strategy="random")
    results_b = await run_simulation_scenario(num_steps=steps, strategy="urgency")
    
    return {
        "comparison": {
            "baseline": results_a,
            "optimized": results_b,
            "delta_completion_rate": round(results_b.get("completion_rate", 0) - results_a.get("completion_rate", 0), 1)
        }
    }
