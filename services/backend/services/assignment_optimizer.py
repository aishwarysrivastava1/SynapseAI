from __future__ import annotations

from services.optimization.reoptimization_engine import optimize_task_assignments as _optimize


async def optimize_task_assignments(
    ngo_id: str,
    tasks: list | None = None,
    volunteers_data: list | None = None,
    *,
    max_assignments: int | None = None,
) -> list[dict]:
    return await _optimize(
        ngo_id=ngo_id,
        tasks=tasks,
        volunteers_data=volunteers_data,
        max_assignments=max_assignments,
    )
