import os
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from services.neo4j_service import neo4j_service
from services.firebase_service import firebase_service
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

SEED_ADMIN_SECRET = os.environ.get("SEED_ADMIN_SECRET")

def _require_seed_secret(x_seed_secret: str = Header(default=None)):
    """Reject any request that does not carry the correct SEED_ADMIN_SECRET header. Use empty secret locally."""
    if SEED_ADMIN_SECRET and x_seed_secret != SEED_ADMIN_SECRET:
        logger.warning("Seed endpoint accessed with invalid secret")
        raise HTTPException(status_code=401, detail="Invalid seed admin secret")

@router.post("", dependencies=[Depends(_require_seed_secret)])
async def seed_graph():
    """Load the Supercharged Urban Flood demo scenario into Neo4j + Firestore."""
    cypher_path = os.path.join(os.path.dirname(__file__), "../../../data/seed_graph.cypher")
    try:
        with open(cypher_path, "r", encoding="utf-8") as f:
            raw = f.read()
        queries = [
            q.strip()
            for q in raw.split("\n\n")
            if q.strip() and not all(line.strip().startswith("//") or not line.strip() for line in q.strip().splitlines())
        ]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Seed file not found at {cypher_path}")

    errors = []
    success_count = 0
    try:
        driver = neo4j_service.get_driver()
        async with driver.session() as session:
            for query in queries:
                try:
                    await session.run(query)
                    success_count += 1
                except Exception as qe:
                    logger.warning(f"Seed query skipped (non-fatal): {qe}")
                    errors.append(1)  # count only; never expose query error text

        logger.info(f"Graph seeded: {success_count} statements executed, {len(errors)} skipped")

        # Seed Firestore with the demo needs for real-time dashboard
        await _seed_firestore_demo()

        return {
            "success": True,
            "statements_executed": success_count,
            "statements_skipped": len(errors),
            "message": f"Supercharged Urban Flood demo loaded: {success_count} Cypher statements executed."
        }
    except Exception as e:
        logger.error(f"Seed error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during DB seeding.")


async def _seed_firestore_demo():
    """Push demo needs, tasks, and volunteers to Firestore so the live dashboard has huge numbers."""
    if not firebase_service.db:
        logger.warning("Firestore not initialised — skipping Firestore seed")
        return

    demo_needs = [
        {"id": "n_flood_main", "type": "infrastructure", "sub_type": "flash_flood",
         "description": "Severe flooding rendering 15,000 homeless. 6ft water logging.",
         "urgency_score": 1.0, "population_affected": 15000, "status": "PENDING",
         "location": {"lat": 19.0530, "lng": 72.8543, "name": "Dharavi, Mumbai"}},
        {"id": "n_road_block", "type": "infrastructure", "sub_type": "road_blockage",
         "description": "Massive landslide blocking all major logistics routes to Dharavi.",
         "urgency_score": 0.95, "population_affected": 25000, "status": "PENDING",
         "location": {"lat": 19.0530, "lng": 72.8543, "name": "Dharavi, Mumbai"}},
        {"id": "n_supply_chain", "type": "food", "sub_type": "supply_disruption",
         "description": "Supply chains completely disrupted, food running out fast.",
         "urgency_score": 0.88, "population_affected": 10500, "status": "PENDING",
         "location": {"lat": 19.0530, "lng": 72.8543, "name": "Dharavi, Mumbai"}},
        {"id": "n_shelter_crisis", "type": "shelter", "sub_type": "displacement",
         "description": "5,000 displaced people requiring mega-camp setup.",
         "urgency_score": 0.92, "population_affected": 5000, "status": "CLAIMED",
         "location": {"lat": 19.0530, "lng": 72.8543, "name": "Dharavi, Mumbai"}},
        {"id": "n_water_contam", "type": "water_sanitation", "sub_type": "contamination",
         "description": "Sewer lines burst, massive drinking water contamination.",
         "urgency_score": 0.93, "population_affected": 22000, "status": "PENDING",
         "location": {"lat": 19.0728, "lng": 72.8826, "name": "Kurla East, Mumbai"}},
        {"id": "n_medical_emerg", "type": "medical", "sub_type": "waterborne_disease",
         "description": "Outbreak of cholera and dengue in relief camps.",
         "urgency_score": 1.0, "population_affected": 1200, "status": "PENDING",
         "location": {"lat": 19.0728, "lng": 72.8826, "name": "Kurla East, Mumbai"}},
        {"id": "n_rescue_ops", "type": "safety", "sub_type": "stranded_persons",
         "description": "150 citizens stranded on building rooftops awaiting airlift.",
         "urgency_score": 1.0, "population_affected": 150, "status": "VERIFIED",
         "location": {"lat": 19.0596, "lng": 72.8295, "name": "Bandra West, Mumbai"}},
        {"id": "n_power_out", "type": "infrastructure", "sub_type": "power_outage",
         "description": "Major grid failure affecting 15 wards. Rescue operations impaired.",
         "urgency_score": 0.85, "population_affected": 140000, "status": "PENDING",
         "location": {"lat": 19.0728, "lng": 72.8826, "name": "Kurla East, Mumbai"}},
    ]

    batch = firebase_service.db.batch()
    for need in demo_needs:
        ref = firebase_service.db.collection("needs").document(need["id"])
        batch.set(ref, {**need, "reported_at": datetime.now(timezone.utc).replace(tzinfo=None), "tasks_spawned": 1})
        task_ref = firebase_service.db.collection("tasks").document(need["id"])
        batch.set(task_ref, {
            "neoNeedId": need["id"],
            "title": f"{need['sub_type'].replace('_', ' ').title()} — {need['location']['name']}",
            "description": need["description"],
            "status": need["status"],
            "createdAt": datetime.now(timezone.utc).replace(tzinfo=None),
            "urgency": need["urgency_score"],
            "location": need["location"],
            "xpReward": int(need["urgency_score"] * 1000),
        })
        
    demo_vols = [
        {"uid": "v_amit", "name": "Amit Kumar", "phone": "+919999999991", "availabilityStatus": "ACTIVE", "totalXP": 6500, "totalTasksCompleted": 85, "reputationScore": 98, "skills": ["medical_aid", "search_rescue"]},
        {"uid": "v_priya", "name": "Priya Sharma", "phone": "+919999999992", "availabilityStatus": "ACTIVE", "totalXP": 4800, "totalTasksCompleted": 52, "reputationScore": 95, "skills": ["water_purification", "logistics"]},
        {"uid": "v_rahul", "name": "Rahul Singh", "phone": "+919999999993", "availabilityStatus": "ACTIVE", "totalXP": 9200, "totalTasksCompleted": 120, "reputationScore": 100, "skills": ["logistics", "community_outreach"]},
        {"uid": "v_meera", "name": "Meera Patel", "phone": "+919999999994", "availabilityStatus": "ACTIVE", "totalXP": 3400, "totalTasksCompleted": 35, "reputationScore": 92, "skills": ["medical_aid"]},
        {"uid": "v_arjun", "name": "Arjun Nair", "phone": "+919999999995", "availabilityStatus": "ACTIVE", "totalXP": 7100, "totalTasksCompleted": 91, "reputationScore": 96, "skills": ["search_rescue", "structural_assessment"]}
    ]
    
    for v in demo_vols:
        v_ref = firebase_service.db.collection("volunteers").document(v["uid"])
        batch.set(v_ref, v)
        
    batch.commit()
    logger.info("Firestore seed: 8 demo needs + 8 tasks + 5 volunteers written")

    # Log activity
    firebase_service.log_activity(
        event_type="SEED_LOADED",
        title="Supercharged Urban Flood Demo Loaded",
        description="Massive scale Mumbai flood scenario seeded with inflated values.",
        metadata={"scenario": "Supercharged Urban Flood", "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
    )


@router.delete("", dependencies=[Depends(_require_seed_secret)])
async def clear_graph():
    """Wipe all nodes from Neo4j and all demo collections from Firestore. Use for repeated demos."""
    try:
        await neo4j_service.run_query("MATCH (n) DETACH DELETE n")
        logger.warning("Graph database cleared by seed admin")

        # Clear Firestore demo collections
        if firebase_service.db:
            for coll in ["needs", "tasks", "activity", "notifications", "volunteers"]:
                docs = firebase_service.db.collection(coll).limit(200).stream()
                batch = firebase_service.db.batch()
                count = 0
                for doc in docs:
                    batch.delete(doc.reference)
                    count += 1
                if count:
                    batch.commit()
            logger.info("Firestore demo collections cleared")

        return {"success": True, "message": "Graph + Firestore cleared. Ready for fresh demo."}
    except Exception as e:
        logger.error(f"Clear graph error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error clearing graph.")
