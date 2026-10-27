// ==============================================================================
// Neo4j Schema Initialization — FamilyVault Graph Service
// Owner: Riya | Sprint 1
// ==============================================================================
// Person.id MUST equal users.id from Postgres (see contracts/schema.sql).
// Never generate an independent ID for a Person node — pass the Postgres UUID
// in on creation.

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT person_id_not_null IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS NOT NULL;