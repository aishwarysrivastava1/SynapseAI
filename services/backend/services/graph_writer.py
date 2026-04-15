from services.neo4j_service import neo4j_service
from services.firebase_service import firebase_service
from typing import Optional, Tuple
import uuid
import logging

logger = logging.getLogger(__name__)

async def write_extraction_to_graph(
    extraction: dict,
    override_coords: Optional[Tuple[float, float]] = None
) -> str:
    """Takes Gemini output, creates all nodes and edges in Neo4j, returns the generated need_id."""
    if "error" in extraction and extraction["error"]:
        logger.error(f"Extraction error: {extraction['error']}")
        return ""
        
    nodes = extraction.get("nodes", [])
    edges = extraction.get("edges", [])
    
    need_node = next((n for n in nodes if n["label"] == "Need"), None)
    if not need_node:
        return ""
        
    need_id = f"n_{uuid.uuid4().hex[:12]}"
    driver = neo4j_service.get_driver()
    
    try:
        async with driver.session() as session:
            # Create Need
            props = need_node.get("properties", {})
            await session.run(
                """
                CREATE (n:Need {
                    id: $id, type: $type, sub_type: $sub_type, 
                    description: $desc, urgency_score: $urg, 
                    population_affected: $pop, status: 'PENDING', 
                    reported_at: datetime()
                }) RETURN n
                """,
                id=need_id,
                type=props.get("type", "unknown"),
                sub_type=props.get("sub_type", ""),
                desc=props.get("description", ""),
                urg=props.get("urgency_score", 0.5),
                pop=props.get("population_affected", 1)
            )

            # Node indices map
            resolved_lat = 0.0
            resolved_lng = 0.0
            idx_map = {}
            for i, node in enumerate(nodes):
                if node["label"] == "Need":
                    idx_map[i] = {"id": need_id, "label": "Need"}
                elif node["label"] == "Location":
                    l_id = f"l_{uuid.uuid4().hex[:12]}"
                    lp = node.get("properties", {})
                    gemini_lat = lp.get("lat") or 0.0
                    gemini_lng = lp.get("lng") or 0.0
                    if override_coords and gemini_lat == 0.0 and gemini_lng == 0.0:
                        lat = override_coords[0]
                        lng = override_coords[1]
                    else:
                        lat = gemini_lat
                        lng = gemini_lng
                    resolved_lat, resolved_lng = lat, lng
                    name = lp.get("name", "Unknown Area")
                    
                    await session.run(
                        """
                        MERGE (l:Location {name: $name})
                        ON CREATE SET l.id = $id, l.ward = $ward, l.lat = $lat, l.lng = $lng,
                        l.point = point({latitude: $lat, longitude: $lng})
                        """,
                        name=name, id=l_id, ward=lp.get("ward", ""), lat=lat, lng=lng
                    )
                    idx_map[i] = {"name": name, "label": "Location"}
                
                elif node["label"] == "Skill":
                    sp = node.get("properties", {})
                    name = sp.get("name", "general")
                    await session.run(
                        """
                        MERGE (s:Skill {name: $name})
                        ON CREATE SET s.category = $cat
                        """,
                        name=name, cat=sp.get("category", "general")
                    )
                    idx_map[i] = {"name": name, "label": "Skill"}

            # Edges
            for edge in edges:
                 from_idx = edge.get("from_index")
                 to_idx = edge.get("to_index")
                 e_type = edge.get("type")
                 
                 f_node = idx_map.get(from_idx)
                 t_node = idx_map.get(to_idx)
                 
                 if f_node and t_node:
                     if f_node["label"] == "Need" and t_node["label"] == "Location":
                         await session.run(
                             "MATCH (n:Need {id: $nid}), (l:Location {name: $lname}) MERGE (n)-[:LOCATED_IN]->(l)",
                             nid=f_node["id"], lname=t_node["name"]
                         )
                     elif f_node["label"] == "Need" and t_node["label"] == "Skill":
                          await session.run(
                             "MATCH (n:Need {id: $nid}), (s:Skill {name: $sname}) MERGE (n)-[:REQUIRES_SKILL]->(s)",
                             nid=f_node["id"], sname=t_node["name"]
                         )
                     # Handle other causal edges if generated in advanced queries

            loc_idx = next((i for i, n in enumerate(nodes) if n["label"] == "Location"), -1)
            loc_node = nodes[loc_idx] if loc_idx != -1 else {}
            lp = loc_node.get("properties", {})
            location_name = lp.get("name", "Unknown Area")
            urgency = props.get("urgency_score", 0.5)
            need_type = props.get("type", "unknown")

            need_payload = {
                "type": need_type,
                "sub_type": props.get("sub_type", ""),
                "description": props.get("description", ""),
                "urgency_score": urgency,
                "population_affected": props.get("population_affected", 1),
                "lat": resolved_lat,
                "lng": resolved_lng,
                "location_name": location_name,
            }

            # Sync need to Firestore for real-time frontend access
            firebase_service.sync_need_to_firestore(need_id, need_payload)

            # Create a task in Firestore for volunteer tracking
            firebase_service.create_task_from_need(need_id, need_payload)

            # Notification
            firebase_service.add_notification(
                title="New Emergency Reported",
                message=f"A new {need_type} need reported in {location_name}. Severity: {urgency*10:.1f}/10",
                n_type="URGENT" if urgency > 0.7 else "INFO"
            )

            # Activity feed event
            firebase_service.log_activity(
                event_type="NEED_REPORTED",
                title=f"New {need_type.title()} Need",
                description=f"{props.get('description', '')[:80]}{'...' if len(props.get('description', '')) > 80 else ''}",
                metadata={
                    "need_id": need_id,
                    "urgency_score": urgency,
                    "location": location_name,
                    "type": need_type,
                }
            )
            
        return need_id
    except Exception as e:
        logger.error(f"Graph writer error: {e}")
        return ""
