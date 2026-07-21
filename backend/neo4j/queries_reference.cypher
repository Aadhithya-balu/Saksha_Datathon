// ============================================================
// Reference Cypher queries used by the AI/ML + backend team
// to power the Network Graph module API endpoints.
// ============================================================

// 1. Ego-network: a person's direct connections
MATCH (p:Criminal {criminal_id: $criminal_id})-[r]-(connected)
RETURN p, r, connected;

// 2. Multi-hop expansion (depth-configurable)
MATCH path = (p:Criminal {criminal_id: $criminal_id})-[*1..$depth]-(connected)
RETURN path;

// 3. Shortest path between two suspects
MATCH (a:Criminal {criminal_id: $from_id}), (b:Criminal {criminal_id: $to_id}),
      path = shortestPath((a)-[*..10]-(b))
RETURN path;

// 4. Community detection (requires Graph Data Science library)
CALL gds.louvain.stream('criminal-network-graph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name, communityId
ORDER BY communityId;

// 5. Shared-organization associates (hidden association detection)
MATCH (c1:Criminal)-[:MEMBER_OF]->(org:Organization)<-[:MEMBER_OF]-(c2:Criminal)
WHERE c1.criminal_id = $criminal_id AND c1 <> c2
RETURN DISTINCT c2.name, org.name;
