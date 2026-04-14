import os
from fastapi import APIRouter, HTTPException
from services.neo4j_service import neo4j_service

router = APIRouter()

@router.post("")
async def seed_graph():
    # Read cypher file
    cypher_path = os.path.join(os.path.dirname(__file__), "../../../data/seed_graph.cypher")
    try:
        with open(cypher_path, "r") as f:
            queries = [q.strip() for q in f.read().split('\n\n') if q.strip() and not q.strip().startswith('//')]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Seed file not found at {cypher_path}")

    success_count = 0
    # Group CREATE statements or run line by line if they are separate
    # To simplify, we can just run the whole script if we pass it correctly or run non-empty blocks.
    try:
        driver = neo4j_service.get_driver()
        async with driver.session() as session:
            for query in queries:
                 await session.run(query)
                 success_count += 1
        return {"success": True, "statements_executed": success_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error during DB seeding.")

@router.delete("")
async def clear_graph():
    cypher = "MATCH (n) DETACH DELETE n"
    try:
        await neo4j_service.run_query(cypher)
        return {"success": True, "message": "Graph database cleared."}
    except Exception as e:
         raise HTTPException(status_code=500, detail="Internal server error clearing graph.")
