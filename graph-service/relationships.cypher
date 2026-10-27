// ==============================================================================
// Relationship Model — FamilyVault Graph Service
// Owner: Riya | Sprint 2
// ==============================================================================
// Person nodes are linked by two relationship types:
//   (:Person)-[:PARENT_OF]->(:Person)   — directed, parent to child
//   (:Person)-[:MARRIED_TO]-(:Person)   — undirected, spouse link
//
// Kinship (e.g. "grandmother", "cousin") is derived at query time via
// shortestPath over these two relationship types — never stored directly,
// so it stays correct even as the tree grows.

// Example seed relationship (for local testing only — real data comes from
// Runeet's seed script via the sync endpoint below):
// MATCH (a:Person {id: $parentId}), (b:Person {id: $childId})
// MERGE (a)-[:PARENT_OF]->(b);