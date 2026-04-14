// SYNAPSE AI - Demo Seed Graph for "Urban Flood Response"

// 1. Locations (Delhi Wards)
CREATE (l1:Location {id: 'l_ward7', name: 'Ward 7, East Delhi', ward: 'Ward 7', lat: 28.6219, lng: 77.2913, point: point({latitude: 28.6219, longitude: 77.2913})})
CREATE (l2:Location {id: 'l_ward8', name: 'Ward 8, Laxmi Nagar', ward: 'Ward 8', lat: 28.6304, lng: 77.2772, point: point({latitude: 28.6304, longitude: 77.2772})})
CREATE (l3:Location {id: 'l_ward9', name: 'Ward 9, Shakarpur', ward: 'Ward 9', lat: 28.6256, lng: 77.2818, point: point({latitude: 28.6256, longitude: 77.2818})})

// 2. Skills
CREATE (s_med:Skill {name: 'first_aid', category: 'medical'})
CREATE (s_water:Skill {name: 'water_testing', category: 'technical'})
CREATE (s_food:Skill {name: 'food_distribution', category: 'logistics'})
CREATE (s_shelt:Skill {name: 'shelter_setup', category: 'construction'})

// 3. Needs (Causal Chain: Flooding -> Contamination -> Disease)
CREATE (n1:Need {id: 'n_flood_1', type: 'infrastructure', sub_type: 'flooding', description: 'Severe street flooding, knee deep water.', urgency_score: 0.9, population_affected: 500, status: 'PENDING', reported_at: datetime()})
CREATE (n2:Need {id: 'n_water_1', type: 'water_sanitation', sub_type: 'contamination', description: 'Drinking water smells like sewage due to flood mix.', urgency_score: 0.85, population_affected: 200, status: 'PENDING', reported_at: datetime()})
CREATE (n3:Need {id: 'n_med_1', type: 'medical', sub_type: 'waterborne_disease', description: '5 children showing signs of cholera.', urgency_score: 1.0, population_affected: 5, status: 'PENDING', reported_at: datetime()})

// Edges for Needs
CREATE (n1)-[:LOCATED_IN]->(l1)
CREATE (n2)-[:LOCATED_IN]->(l1)
CREATE (n3)-[:LOCATED_IN]->(l1)
CREATE (n1)-[:CAUSED_BY]->(n2)
CREATE (n2)-[:CAUSED_BY]->(n3)

CREATE (n2)-[:REQUIRES_SKILL]->(s_water)
CREATE (n3)-[:REQUIRES_SKILL]->(s_med)

// Adding more random needs to fill the map
CREATE (n4:Need {id: 'n_food_1', type: 'food', sub_type: 'ration_shortage', description: 'Families trapped without food access for 2 days.', urgency_score: 0.7, population_affected: 50, status: 'PENDING', reported_at: datetime()})-[:LOCATED_IN]->(l2)
CREATE (n4)-[:REQUIRES_SKILL]->(s_food)

CREATE (n5:Need {id: 'n_shelt_1', type: 'shelter', sub_type: 'roof_collapse', description: 'Temporary tin roof collapsed in rain.', urgency_score: 0.6, population_affected: 4, status: 'PENDING', reported_at: datetime()})-[:LOCATED_IN]->(l3)
CREATE (n5)-[:REQUIRES_SKILL]->(s_shelt)

// 4. Volunteers
CREATE (v1:Volunteer {id: 'v_amit', name: 'Amit Kumar', phone: '+919999999991', reputation_score: 95, availability_status: 'ACTIVE', current_active_tasks: 0, total_tasks_completed: 12, total_xp: 450})
CREATE (v2:Volunteer {id: 'v_priya', name: 'Priya Sharma', phone: '+919999999992', reputation_score: 88, availability_status: 'ACTIVE', current_active_tasks: 0, total_tasks_completed: 5, total_xp: 120})
CREATE (v3:Volunteer {id: 'v_rahul', name: 'Rahul Singh', phone: '+919999999993', reputation_score: 100, availability_status: 'ACTIVE', current_active_tasks: 0, total_tasks_completed: 40, total_xp: 2100})

// Edges for Volunteers
CREATE (v1)-[:LOCATED_IN]->(l1)
CREATE (v2)-[:LOCATED_IN]->(l2)
CREATE (v3)-[:LOCATED_IN]->(l3)

CREATE (v1)-[:HAS_SKILL]->(s_med)
CREATE (v2)-[:HAS_SKILL]->(s_water)
CREATE (v3)-[:HAS_SKILL]->(s_food)
CREATE (v3)-[:HAS_SKILL]->(s_shelt)
