// ==============================================================================
// Trustee Graph — FamilyVault Graph Service
// Owner: Riya | Sprint 5 Deliverable 5
// ==============================================================================
// The TRUSTEE_FOR relationship links a :Person node (the trustee) to a
// :Document node (the digital will / time capsule) they are authorised to
// sign off.  This enables graph traversal queries that:
//   a) identify all trustees for a given document in O(1) hops, and
//   b) compute generational distance from the testator (document uploader)
//      by combining TRUSTEE_FOR with PARENT_OF / MARRIED_TO edges.
//
// Schema contract:
//   (:Person)-[:TRUSTEE_FOR {signed_at: <ISO-8601 | null>, role: "PRIMARY"|"BACKUP"}]->(:Document)
//
// Document nodes mirror the documents.id UUID from Postgres.
// Person nodes mirror the users.id UUID from Postgres.
// Both IDs are passed in on creation — never independently generated.
// ==============================================================================

// -- 0. Constraint: Document.id must be unique (analogous to Person.id) --------
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT document_id_not_null IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS NOT NULL;

// -- 1. Upsert a :Document node (called by Runeet's vault on doc creation) -----
// Parameters: $doc_id, $title, $category, $capsule_status,
//             $trustee_approvals_required, $testator_id, $time_capsule_unlock_at
MERGE (d:Document {id: $doc_id})
SET   d.title                       = $title,
      d.category                    = $category,
      d.capsule_status              = $capsule_status,
      d.trustee_approvals_required  = $trustee_approvals_required,
      d.testator_id                 = $testator_id,
      d.time_capsule_unlock_at      = $time_capsule_unlock_at
RETURN d.id AS id;

// -- 2. Register a trustee: (:Person)-[:TRUSTEE_FOR]->(:Document) --------------
// Parameters: $trustee_id, $doc_id, $role ("PRIMARY"|"BACKUP")
// signed_at is null until the trustee actually calls POST /vault/{doc_id}/sign.
MATCH (p:Person   {id: $trustee_id})
MATCH (d:Document {id: $doc_id})
MERGE (p)-[r:TRUSTEE_FOR {role: $role}]->(d)
ON CREATE SET r.signed_at   = null,
              r.assigned_at = datetime()
ON MATCH  SET r.role        = $role
RETURN p.id AS trustee_id, d.id AS doc_id, r.role AS role;

// -- 3. Mark a trustee signature (called when POST /vault/{doc_id}/sign fires) -
// Parameters: $trustee_id, $doc_id
MATCH (p:Person {id: $trustee_id})-[r:TRUSTEE_FOR]->(d:Document {id: $doc_id})
SET   r.signed_at = datetime()
RETURN p.id AS trustee_id, d.id AS doc_id, r.signed_at AS signed_at;

// -- 4. Fetch all trustees for a document with generational distance -----------
// Parameters: $doc_id
// generational_distance = shortestPath hops from trustee to testator via
// PARENT_OF|MARRIED_TO edges (0 = self, 1 = parent/child, etc.)
MATCH (p:Person)-[:TRUSTEE_FOR]->(d:Document {id: $doc_id})
MATCH (testator:Person {id: d.testator_id})
OPTIONAL MATCH path = shortestPath(
    (p)-[:PARENT_OF|MARRIED_TO*0..8]-(testator)
)
RETURN p.id              AS trustee_id,
       p.full_name       AS full_name,
       p.gender          AS gender,
       p.generation      AS generation,
       p.birth_date      AS birth_date,
       p.nuclear_household AS nuclear_household,
       length(path)      AS generational_distance,
       [(p)-[r:TRUSTEE_FOR]->(d) | {role: r.role, signed_at: r.signed_at, assigned_at: r.assigned_at}][0] AS trustee_meta
ORDER BY generational_distance ASC, p.generation ASC;

// -- 5. All documents for which a person is a trustee (reverse traversal) ------
// Parameters: $trustee_id
MATCH (p:Person {id: $trustee_id})-[r:TRUSTEE_FOR]->(d:Document)
RETURN d.id                          AS doc_id,
       d.title                        AS title,
       d.category                     AS category,
       d.capsule_status               AS capsule_status,
       d.trustee_approvals_required   AS required,
       d.time_capsule_unlock_at       AS unlock_at,
       r.role                         AS trustee_role,
       r.signed_at                    AS signed_at;
