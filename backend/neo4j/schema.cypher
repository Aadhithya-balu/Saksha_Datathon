// ============================================================
// SAKSHA — Neo4j Graph Schema
// Nodes: Criminal, Victim, Officer, Case, Vehicle, Weapon, Organization, Location
// Relationships: KNOWS, ASSOCIATED_WITH, USED, ARRESTED_BY, INVESTIGATED_BY,
//                MEMBER_OF, VISITED, OWNS
// ============================================================

// --- Constraints (uniqueness + existence) ---
CREATE CONSTRAINT criminal_id_unique IF NOT EXISTS
FOR (c:Criminal) REQUIRE c.criminal_id IS UNIQUE;

CREATE CONSTRAINT victim_id_unique IF NOT EXISTS
FOR (v:Victim) REQUIRE v.victim_id IS UNIQUE;

CREATE CONSTRAINT officer_id_unique IF NOT EXISTS
FOR (o:Officer) REQUIRE o.officer_id IS UNIQUE;

CREATE CONSTRAINT case_id_unique IF NOT EXISTS
FOR (ca:Case) REQUIRE ca.case_id IS UNIQUE;

CREATE CONSTRAINT vehicle_id_unique IF NOT EXISTS
FOR (ve:Vehicle) REQUIRE ve.vehicle_id IS UNIQUE;

CREATE CONSTRAINT weapon_id_unique IF NOT EXISTS
FOR (w:Weapon) REQUIRE w.weapon_id IS UNIQUE;

CREATE CONSTRAINT organization_id_unique IF NOT EXISTS
FOR (org:Organization) REQUIRE org.organization_id IS UNIQUE;

CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

// --- Indexes for fast lookup by name (search-by-name UX in the app) ---
CREATE INDEX criminal_name_idx IF NOT EXISTS FOR (c:Criminal) ON (c.name);
CREATE INDEX victim_name_idx IF NOT EXISTS FOR (v:Victim) ON (v.name);
CREATE INDEX case_number_idx IF NOT EXISTS FOR (ca:Case) ON (ca.case_number);


// ============================================================
// Sample graph — mirrors a small slice of the Postgres data
// so frontend/AI teams can develop against real-shaped data
// without needing the full pipeline wired up yet.
// ============================================================

MERGE (c1:Criminal {criminal_id: "CRM-10432", name: "Suspect A", status: "at_large"})
MERGE (c2:Criminal {criminal_id: "CRM-10433", name: "Associate B", status: "arrested"})
MERGE (v1:Victim {victim_id: "VIC-2091", name: "Complainant X"})
MERGE (o1:Officer {officer_id: "OFF-771", name: "Inspector Rao", station: "Ashok Nagar PS"})
MERGE (ca1:Case {case_id: "CR-2026-004521", case_number: "CR-2026-004521", crime_type: "Theft"})
MERGE (ve1:Vehicle {vehicle_id: "VEH-501", reg_number: "KA-01-AB-1234", type: "two_wheeler"})
MERGE (w1:Weapon {weapon_id: "WPN-101", type: "knife"})
MERGE (org1:Organization {organization_id: "ORG-9", name: "Unnamed Local Group"})
MERGE (l1:Location {location_id: "LOC-220", name: "MG Road Junction", district: "Bengaluru Urban"})

MERGE (c1)-[:KNOWS {confidence: 0.87}]->(c2)
MERGE (c1)-[:ASSOCIATED_WITH]->(org1)
MERGE (c2)-[:MEMBER_OF]->(org1)
MERGE (c1)-[:USED]->(ve1)
MERGE (c1)-[:USED]->(w1)
MERGE (c1)-[:VISITED]->(l1)
MERGE (ca1)-[:INVESTIGATED_BY]->(o1)
MERGE (c1)-[:ARRESTED_BY]->(o1)
MERGE (v1)-[:VISITED]->(l1)
MERGE (ca1)-[:OWNS]->(l1);
