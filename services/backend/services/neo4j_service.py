import os
import logging
from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

SCHEMA_QUERIES = [
    "CREATE CONSTRAINT need_id IF NOT EXISTS FOR (n:Need) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT volunteer_id IF NOT EXISTS FOR (v:Volunteer) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",
    "CREATE POINT INDEX location_point IF NOT EXISTS FOR (l:Location) ON (l.point)",
]

class Neo4jService:
    def __init__(self):
        self._driver = None
        
    def get_driver(self):
        if not self._driver:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "testpassword")
            self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        return self._driver

    async def close_driver(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def run_query(self, cypher: str, params: dict = None) -> list[dict]:
        params = params or {}
        try:
            driver = self.get_driver()
            async with driver.session() as session:
                result = await session.run(cypher, **params)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Neo4j query failed: {e} | Query: {cypher}")
            return []

    async def initialize_schema(self):
        logger.info("Initializing Neo4j schema constraints and indexes...")
        for query in SCHEMA_QUERIES:
            await self.run_query(query)

neo4j_service = Neo4jService()
