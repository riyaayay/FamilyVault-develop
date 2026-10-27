"""
trustee.py — Sprint 5 Deliverable 5 (Riya)
===========================================
Graph Service module: Neo4j TRUSTEE_FOR relationship management.

Responsibilities:
  - Upsert :Document nodes into Neo4j (mirrors Postgres documents.id).
  - Create (:Person)-[:TRUSTEE_FOR]->(:Document) edges.
  - Mark trustee signatures when vault sign-off fires.
  - Traverse graph to return all trustees + generational distance from
    the testator, enabling Runeet's quorum check and Anushka's
    MilestoneNodeBadge to show live signature progress.

Follows the same structural patterns as kinship.py (Sprint 3/4).
Neo4j max_depth parameters are inlined into Cypher strings — they cannot
be passed as Cypher $params for variable-length path patterns.
"""
from db import get_driver, NEO4J_DATABASE


# ---------------------------------------------------------------------------
# Document node sync
# ---------------------------------------------------------------------------

def upsert_document(
    doc_id: str,
    title: str,
    category: str,
    capsule_status: str,
    testator_id: str,
    trustee_approvals_required: int = 0,
    time_capsule_unlock_at: str = None,
) -> dict:
    """Sprint 5 D5 (Riya) — upsert a :Document node into Neo4j.

    Called automatically by the graph-service endpoint whenever Runeet's
    backend creates or updates a vault document that requires trustee
    governance.  The Document node is the target of TRUSTEE_FOR edges.

    Args:
        doc_id:                      documents.id UUID from Postgres.
        title:                       Human-readable document title.
        category:                    e.g. "LEGACY_WILL", "TIME_CAPSULE".
        capsule_status:              "LOCKED" | "TRUSTEE_PENDING" | "RELEASED".
        testator_id:                 Person UUID of the document uploader.
        trustee_approvals_required:  Quorum size Runeet set on the document.
        time_capsule_unlock_at:      ISO-8601 unlock timestamp (nullable).

    Returns:
        {"status": "created"|"updated", "id": doc_id}
    """
    driver = get_driver()

    def _upsert(tx):
        result = tx.run(
            """
            MERGE (d:Document {id: $docId})
            SET   d.title                      = $title,
                  d.category                   = $category,
                  d.capsule_status             = $capsuleStatus,
                  d.trustee_approvals_required = $trusteesRequired,
                  d.testator_id                = $testatorId,
                  d.time_capsule_unlock_at     = $unlockAt
            RETURN d.id AS id
            """,
            docId=doc_id,
            title=title,
            category=category,
            capsuleStatus=capsule_status,
            trusteesRequired=trustee_approvals_required,
            testatorId=testator_id,
            unlockAt=time_capsule_unlock_at,
        )
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_write(_upsert)

    if record is None:
        return None
    return {"status": "upserted", "id": record["id"]}


# ---------------------------------------------------------------------------
# Trustee relationship management
# ---------------------------------------------------------------------------

def assign_trustee(trustee_id: str, doc_id: str, role: str = "PRIMARY") -> dict:
    """Sprint 5 D5 (Riya) — create (:Person)-[:TRUSTEE_FOR]->(:Document).

    Uses MERGE so calling this endpoint twice for the same (trustee, doc)
    pair is idempotent — it simply updates the role rather than creating a
    duplicate edge.

    Args:
        trustee_id:  Person UUID (must already exist as a :Person node).
        doc_id:      Document UUID (must already exist as a :Document node).
        role:        "PRIMARY" (counted toward quorum) or "BACKUP" (observer).

    Returns:
        {trustee_id, doc_id, role, assigned_at} or None if nodes not found.
    """
    driver = get_driver()

    def _assign(tx):
        result = tx.run(
            """
            MATCH (p:Person   {id: $trusteeId})
            MATCH (d:Document {id: $docId})
            MERGE (p)-[r:TRUSTEE_FOR {role: $role}]->(d)
            ON CREATE SET r.signed_at   = null,
                          r.assigned_at = datetime()
            ON MATCH  SET r.role        = $role
            RETURN p.id AS trustee_id,
                   d.id AS doc_id,
                   r.role AS role,
                   toString(r.assigned_at) AS assigned_at
            """,
            trusteeId=trustee_id,
            docId=doc_id,
            role=role,
        )
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_write(_assign)

    if record is None:
        return None

    return {
        "trustee_id":  record["trustee_id"],
        "doc_id":      record["doc_id"],
        "role":        record["role"],
        "assigned_at": record["assigned_at"],
    }


def record_trustee_signature(trustee_id: str, doc_id: str) -> dict:
    """Sprint 5 D5 (Riya) — stamp signed_at on the TRUSTEE_FOR edge.

    Called by main.py's sign endpoint to mirror the Postgres sign-off in
    the graph so Anushka's live badge can query purely from Neo4j without
    needing a Postgres round-trip for signature status.

    Returns:
        {trustee_id, doc_id, signed_at} or None if edge not found.
    """
    driver = get_driver()

    def _sign(tx):
        result = tx.run(
            """
            MATCH (p:Person {id: $trusteeId})-[r:TRUSTEE_FOR]->(d:Document {id: $docId})
            SET   r.signed_at = datetime()
            RETURN p.id AS trustee_id,
                   d.id AS doc_id,
                   toString(r.signed_at) AS signed_at
            """,
            trusteeId=trustee_id,
            docId=doc_id,
        )
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_write(_sign)

    if record is None:
        return None

    return {
        "trustee_id": record["trustee_id"],
        "doc_id":     record["doc_id"],
        "signed_at":  record["signed_at"],
    }


# ---------------------------------------------------------------------------
# Graph traversal queries
# ---------------------------------------------------------------------------

def get_trustees_for_document(doc_id: str, max_depth: int = 8) -> list:
    """Sprint 5 D5 (Riya) — return all trustees of a document with
    generational distance from the testator.

    Traverses (:Person)-[:TRUSTEE_FOR]->(:Document) then computes
    shortestPath between each trustee and the testator via PARENT_OF and
    MARRIED_TO edges (max_depth hops).

    Response shape per trustee:
        {
          trustee_id, full_name, gender, generation, birth_date,
          nuclear_household, generational_distance,
          role, signed_at, assigned_at, has_signed
        }

    Returns [] when the Document node has no TRUSTEE_FOR edges.
    Returns None when the Document node itself does not exist.
    """
    driver = get_driver()
    max_depth = int(max_depth)

    # Check document exists first
    def _doc_exists(tx):
        r = tx.run(
            "MATCH (d:Document {id: $docId}) RETURN d.testator_id AS testatorId",
            docId=doc_id,
        )
        return r.single()

    def _read(tx):
        result = tx.run(
            f"""
            MATCH (p:Person)-[r:TRUSTEE_FOR]->(d:Document {{id: $docId}})
            MATCH (testator:Person {{id: d.testator_id}})
            OPTIONAL MATCH path = shortestPath(
                (p)-[:PARENT_OF|MARRIED_TO*0..{max_depth}]-(testator)
            )
            RETURN p.id                AS trustee_id,
                   p.full_name        AS full_name,
                   p.gender           AS gender,
                   p.generation       AS generation,
                   p.birth_date       AS birth_date,
                   p.nuclear_household AS nuclear_household,
                   length(path)       AS generational_distance,
                   r.role             AS role,
                   toString(r.signed_at)   AS signed_at,
                   toString(r.assigned_at) AS assigned_at
            ORDER BY generational_distance ASC, p.generation ASC
            """,
            docId=doc_id,
        )
        return [
            {
                "trustee_id":            rec["trustee_id"],
                "full_name":             rec["full_name"],
                "gender":                rec["gender"],
                "generation":            rec["generation"],
                "birth_date":            rec["birth_date"],
                "nuclear_household":     rec["nuclear_household"],
                "generational_distance": rec["generational_distance"],
                "role":                  rec["role"],
                "signed_at":             rec["signed_at"],
                "assigned_at":           rec["assigned_at"],
                "has_signed":            rec["signed_at"] is not None,
            }
            for rec in result
        ]

    with driver.session(database=NEO4J_DATABASE) as session:
        doc_record = session.execute_read(_doc_exists)
        if doc_record is None:
            return None          # caller raises 404
        trustees = session.execute_read(_read)

    return trustees


def get_documents_for_trustee(trustee_id: str) -> list:
    """Sprint 5 D5 (Riya) — reverse traversal: all documents for which
    a given person is a registered trustee.

    Useful for:
      - Anushka's MilestoneNodeBadge counting pending signature obligations
        per family member node on the canvas.
      - Runeet's quorum audit dashboard.

    Returns [] when person is not a trustee for any document.
    Returns None when the Person node does not exist.
    """
    driver = get_driver()

    def _person_exists(tx):
        r = tx.run(
            "MATCH (p:Person {id: $pid}) RETURN p.id AS id",
            pid=trustee_id,
        )
        return r.single()

    def _read(tx):
        result = tx.run(
            """
            MATCH (p:Person {id: $pid})-[r:TRUSTEE_FOR]->(d:Document)
            RETURN d.id                        AS doc_id,
                   d.title                     AS title,
                   d.category                  AS category,
                   d.capsule_status            AS capsule_status,
                   d.trustee_approvals_required AS required,
                   d.time_capsule_unlock_at     AS unlock_at,
                   d.testator_id               AS testator_id,
                   r.role                      AS trustee_role,
                   toString(r.signed_at)       AS signed_at,
                   toString(r.assigned_at)     AS assigned_at
            ORDER BY d.time_capsule_unlock_at ASC
            """,
            pid=trustee_id,
        )
        return [
            {
                "doc_id":       rec["doc_id"],
                "title":        rec["title"],
                "category":     rec["category"],
                "status":       rec["capsule_status"],
                "required":     rec["required"],
                "unlock_at":    rec["unlock_at"],
                "testator_id":  rec["testator_id"],
                "trustee_role": rec["trustee_role"],
                "signed_at":    rec["signed_at"],
                "assigned_at":  rec["assigned_at"],
                "has_signed":   rec["signed_at"] is not None,
            }
            for rec in result
        ]

    with driver.session(database=NEO4J_DATABASE) as session:
        person_rec = session.execute_read(_person_exists)
        if person_rec is None:
            return None
        docs = session.execute_read(_read)

    return docs
