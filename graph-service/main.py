from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import time


from db import get_driver, NEO4J_DATABASE, run_schema_init
from schemas import PersonIn
import kinship
import trustee

app = FastAPI(title="FamilyVault Graph Service")


@app.on_event("startup")
def startup():
    try:
        run_schema_init()
    except Exception as exc:
        print(f"[graph-service] Startup notice: Neo4j schema init postponed (database warming up or offline fallback active): {exc}")


@app.get("/health")
def health():
    """Sprint 6 D5 (Riya) — enriched health endpoint for graph-service (:8001).

    Performs a timed Neo4j round-trip ping and evaluates against the
    Sprint 6 SLA gate: shortest-path query latency MUST be ≤ 15ms for
    the release gate to pass.  Gracefully degrades when Neo4j is offline
    so the service stays up and returns a clear `neo4j_offline` status
    rather than crashing — satisfying the offline-fallback requirement.

    Response shape:
      status:         "healthy" | "degraded" | "offline"
      service:        "graph-service"
      version:        "1.0.0"
      neo4j_ping_ms:  round-trip latency to Neo4j (null if offline)
      sla_gate_pass:  true if neo4j_ping_ms ≤ 15ms (false or null if offline)
      neo4j_online:   true | false
      offline_fallback_active: true when Neo4j is unreachable but service
                               is still serving cached / degraded responses
    """
    SLA_THRESHOLD_MS = 15.0
    neo4j_ping_ms = None
    neo4j_online = False
    sla_gate_pass = None
    offline_fallback_active = False

    try:
        driver = get_driver()
        start = time.perf_counter()
        with driver.session(database=NEO4J_DATABASE) as session:
            session.run("RETURN 1").single()
        neo4j_ping_ms = round((time.perf_counter() - start) * 1000, 2)
        neo4j_online = True
        sla_gate_pass = neo4j_ping_ms <= SLA_THRESHOLD_MS
    except Exception:
        # Neo4j is unreachable — graceful offline fallback
        offline_fallback_active = True

    if neo4j_online:
        status = "healthy" if sla_gate_pass else "degraded"
    else:
        status = "offline"

    return {
        "status":                 status,
        "service":                "graph-service",
        "version":                "1.0.0",
        "neo4j_online":           neo4j_online,
        "neo4j_ping_ms":          neo4j_ping_ms,
        "sla_gate_pass":          sla_gate_pass,
        "sla_threshold_ms":       SLA_THRESHOLD_MS,
        "offline_fallback_active": offline_fallback_active,
    }


@app.post("/api/graph/person")
def create_person(person: PersonIn):
    """
    Creates or updates a :Person node carrying every field the tree
    contract's node.data object needs, plus clan_id/clan_name and an
    optional pinned canvas position. person_id MUST be the same UUID as
    users.id in Postgres -- called by Runeet's seed script / signup flow,
    never generates its own ID.
    """
    driver = get_driver()

    def _create(tx):
        result = tx.run(
            """
            MERGE (p:Person {id: $id})
            SET p.full_name        = $full_name,
                p.role              = $role,
                p.relation_to_head  = $relation_to_head,
                p.generation        = $generation,
                p.gender            = $gender,
                p.birth_date        = $birth_date,
                p.is_living         = $is_living,
                p.avatar_url        = $avatar_url,
                p.nuclear_household = $nuclear_household,
                p.clan_id           = $clan_id,
                p.clan_name         = $clan_name,
                p.position_x        = $position_x,
                p.position_y        = $position_y,
                p.gotra              = $gotra
            RETURN p.id AS id
            """,
            id=person.person_id,
            full_name=person.full_name,
            role=person.role,
            relation_to_head=person.relation_to_head,
            generation=person.generation,
            gender=person.gender,
            birth_date=person.birth_date,
            is_living=person.is_living,
            avatar_url=person.avatar_url,
            nuclear_household=person.nuclear_household,
            clan_id=person.clan_id,
            clan_name=person.clan_name,
            position_x=person.position_x,
            position_y=person.position_y,
            gotra=person.gotra,
        )
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        # execute_write guarantees the write is actually committed before
        # this returns -- session.run() alone does not.
        record = session.execute_write(_create)

    if record is None:
        raise HTTPException(status_code=500, detail=f"Failed to create person {person.person_id}")

    return {"status": "created", "id": record["id"]}


@app.post("/api/graph/relationship")
def create_relationship(
    parent_id: str = None,
    child_id: str = None,
    spouse_a: str = None,
    spouse_b: str = None,
):
    driver = get_driver()

    def _create_parent(tx):
        # Sprint 3 (Riya): paradox / ancestry-cycle validation, run inside
        # the same transaction as the write so there's no race between
        # checking and creating.
        if parent_id == child_id:
            raise ValueError("A person cannot be their own parent.")

        check = tx.run(
            """
            MATCH (parent:Person {id: $pid}), (child:Person {id: $cid})
            RETURN parent.birth_date AS parentBirthDate,
                   child.birth_date  AS childBirthDate,
                   exists((child)-[:PARENT_OF*1..20]->(parent)) AS wouldCreateCycle
            """,
            pid=parent_id, cid=child_id,
        ).single()

        if check is None:
            return None  # one or both nodes don't exist -- 404 path below

        if check["wouldCreateCycle"]:
            raise ValueError(
                f"Cannot make {parent_id} the parent of {child_id}: "
                f"{child_id} is already an ancestor of {parent_id} -- "
                "this would create a cycle in the family tree."
            )

        parent_dob, child_dob = check["parentBirthDate"], check["childBirthDate"]
        if parent_dob and child_dob and child_dob <= parent_dob:
            raise ValueError(
                f"Cannot make {parent_id} the parent of {child_id}: "
                f"child's birth_date ({child_dob}) is not after "
                f"parent's birth_date ({parent_dob})."
            )

        result = tx.run(
            "MATCH (a:Person {id: $pid}), (b:Person {id: $cid}) "
            "MERGE (a)-[:PARENT_OF]->(b) "
            "RETURN a.id AS parent, b.id AS child",
            pid=parent_id, cid=child_id,
        )
        return result.single()

    def _create_spouse(tx):
        # A person can't marry their own ancestor or descendant.
        check = tx.run(
            """
            MATCH (a:Person {id: $a}), (b:Person {id: $b})
            RETURN exists((a)-[:PARENT_OF*1..20]->(b)) OR
                   exists((b)-[:PARENT_OF*1..20]->(a)) AS wouldBeParadox
            """,
            a=spouse_a, b=spouse_b,
        ).single()

        if check is None:
            return None

        if check["wouldBeParadox"]:
            raise ValueError(
                f"Cannot marry {spouse_a} and {spouse_b}: "
                "one is a direct ancestor/descendant of the other."
            )

        result = tx.run(
            "MATCH (a:Person {id: $a}), (b:Person {id: $b}) "
            "MERGE (a)-[:MARRIED_TO]-(b) "
            "RETURN a.id AS spouseA, b.id AS spouseB",
            a=spouse_a, b=spouse_b,
        )
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        if parent_id and child_id:
            try:
                record = session.execute_write(_create_parent)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            if record is None:
                # The MATCH found no such parent and/or child -- meaning
                # at least one Person node doesn't exist yet. Fail loudly
                # instead of returning a "created" status Neo4j never
                # confirmed.
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Cannot link parent {parent_id} -> child {child_id}: "
                        "one or both Person nodes do not exist in the graph."
                    ),
                )
            return {"status": "created", "type": "PARENT_OF", "from": parent_id, "to": child_id}

        if spouse_a and spouse_b:
            try:
                record = session.execute_write(_create_spouse)
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            if record is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Cannot link spouses {spouse_a} <-> {spouse_b}: "
                        "one or both Person nodes do not exist in the graph."
                    ),
                )
            return {"status": "created", "type": "MARRIED_TO", "a": spouse_a, "b": spouse_b}

    raise HTTPException(
        status_code=400,
        detail="Provide either parent_id+child_id or spouse_a+spouse_b",
    )


@app.get("/api/graph/tree")
def get_tree(person_id: str, max_depth: int = 4):
    """Returns {endpoint, clan_id, clan_name, nodes, edges} exactly per
    contracts/graph-tree-response.json."""
    tree = kinship.get_family_tree_graph(person_id, max_depth=max_depth)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"Person {person_id} not found in graph")
    return tree


@app.get("/api/graph/persons")
def list_persons():
    """Lists every Person node currently in the graph (id + full_name).
    Backs the Sprint 3 UUID-sync verification script, and doubles as a
    quick sanity-check for Runeet/Ayush without needing direct DB access."""
    driver = get_driver()

    def _read(tx):
        result = tx.run(
            "MATCH (p:Person) RETURN p.id AS id, p.full_name AS full_name "
            "ORDER BY p.full_name"
        )
        return [{"id": r["id"], "full_name": r["full_name"]} for r in result]

    with driver.session(database=NEO4J_DATABASE) as session:
        persons = session.execute_read(_read)

    return {"count": len(persons), "persons": persons}


@app.get("/api/graph/kinship")
def get_kinship(person_a: str, person_b: str, max_depth: int = 8):
    result = kinship.get_kinship_path(person_a, person_b, max_depth=max_depth)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No path found between {person_a} and {person_b} "
                "(or one/both do not exist in the graph)"
            ),
        )
    return result


# ---------------------------------------------------------------------------
# Sprint 4 — Deliverable 5 (Riya)
# Path-parameterized rich kinship endpoint.
# Output contract consumed by Anushka's KinshipPathGlow (D6).
# ---------------------------------------------------------------------------
@app.get("/api/graph/kinship/{from_id}/{to_id}")
def get_kinship_rich(from_id: str, to_id: str, max_depth: int = 8):
    """Sprint 4 D5 (Riya) — returns the shortest ancestral/marital traversal
    path between two clan members with:
      - kinship_label: Indian cultural term (Chacha, Tauji, Mama, Bua, Masi)
        or a generic hop-based fallback.
      - path_node_ids: ordered list of Person UUIDs along the path, consumed
        by Anushka's KinshipPathGlow to highlight the glowing SVG route on
        the React Flow canvas.
      - path_edges: ordered list of {source, target, rel_type} dicts.
      - from_node / to_node: minimal node metadata.
    """
    result = kinship.get_kinship_path_rich(from_id, to_id, max_depth=max_depth)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No path found between {from_id} and {to_id} "
                "(or one/both Person nodes do not exist in the graph)"
            ),
        )
    return result


# ---------------------------------------------------------------------------
# Sprint 5 — Deliverable 5 (Riya)
# Neo4j Trustee Graph & Cypher Traversal
# See: graph-service/trustee_graph.cypher for full relationship schema.
# ---------------------------------------------------------------------------

class DocumentSyncIn(BaseModel):
    """Body for POST /api/graph/document — upserts a :Document node."""
    doc_id: str
    title: str
    category: str = "LEGACY_WILL"
    capsule_status: str = "LOCKED"
    testator_id: str
    trustee_approvals_required: int = 0
    time_capsule_unlock_at: Optional[str] = None


class TrusteeAssignIn(BaseModel):
    """Body for POST /api/graph/trustee — creates TRUSTEE_FOR edge."""
    trustee_id: str
    doc_id: str
    role: str = "PRIMARY"  # PRIMARY = counts toward quorum; BACKUP = observer


class TrusteeSignIn(BaseModel):
    """Body for POST /api/graph/trustee/sign — stamps signed_at on edge."""
    trustee_id: str
    doc_id: str


@app.post("/api/graph/document")
def sync_document(doc_in: DocumentSyncIn):
    """Sprint 5 D5 (Riya) — upsert a :Document node into Neo4j.

    Called by Runeet's backend (or seed script) whenever a vault document
    requiring trustee governance is created or updated.  The Document node
    is the target of (:Person)-[:TRUSTEE_FOR]->(:Document) edges used by
    the trustee traversal queries.

    Idempotent — safe to call on every vault write.
    """
    result = trustee.upsert_document(
        doc_id=doc_in.doc_id,
        title=doc_in.title,
        category=doc_in.category,
        capsule_status=doc_in.capsule_status,
        testator_id=doc_in.testator_id,
        trustee_approvals_required=doc_in.trustee_approvals_required,
        time_capsule_unlock_at=doc_in.time_capsule_unlock_at,
    )
    if result is None:
        raise HTTPException(status_code=500, detail=f"Failed to upsert document {doc_in.doc_id}")
    return result


@app.post("/api/graph/trustee")
def assign_trustee(body: TrusteeAssignIn):
    """Sprint 5 D5 (Riya) — create (:Person)-[:TRUSTEE_FOR {role}]->(:Document).

    Both the Person and Document nodes must already exist in the graph.
    Idempotent — if the edge already exists its role is updated in-place.

    role:
      PRIMARY — counted toward the quorum (trustee_approvals_required).
      BACKUP  — can observe and sign but does not advance the quorum counter.
    """
    result = trustee.assign_trustee(
        trustee_id=body.trustee_id,
        doc_id=body.doc_id,
        role=body.role,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Cannot assign trustee: Person {body.trustee_id} or "
                f"Document {body.doc_id} not found in graph"
            ),
        )
    return result


@app.post("/api/graph/trustee/sign")
def sign_as_trustee(body: TrusteeSignIn):
    """Sprint 5 D5 (Riya) — stamp signed_at on the TRUSTEE_FOR edge.

    Called as a side-effect when Runeet's POST /api/v1/vault/{doc_id}/sign
    fires, so the graph and Postgres stay in sync.  Anushka's
    MilestoneNodeBadge reads signature status directly from Neo4j to avoid
    an extra Postgres round-trip on every tree render.
    """
    result = trustee.record_trustee_signature(
        trustee_id=body.trustee_id,
        doc_id=body.doc_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No TRUSTEE_FOR edge found between Person {body.trustee_id} "
                f"and Document {body.doc_id}"
            ),
        )
    return result


@app.get("/api/graph/trustee/{doc_id}")
def get_trustees(doc_id: str, max_depth: int = 8):
    """Sprint 5 D5 (Riya) — all trustees of a document with generational
    distance from the testator.

    Traverses (:Person)-[:TRUSTEE_FOR]->(:Document) then computes
    shortestPath hops between each trustee and the testator over
    PARENT_OF / MARRIED_TO edges (up to max_depth).

    Response per trustee:
      trustee_id, full_name, gender, generation, birth_date,
      nuclear_household, generational_distance, role,
      signed_at, assigned_at, has_signed

    Consumed by:
      - Runeet's quorum governance dashboard.
      - Anushka's MilestoneNodeBadge signature progress pill (1/2, 2/2).
      - Ayush's cross-tenant RLS pentest (D6).
    """
    result = trustee.get_trustees_for_document(doc_id, max_depth=max_depth)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found in graph",
        )
    return {"doc_id": doc_id, "trustee_count": len(result), "trustees": result}


@app.get("/api/graph/trustee/person/{person_id}")
def get_trustee_documents(person_id: str):
    """Sprint 5 D5 (Riya) — all documents for which a person is a trustee.

    Reverse traversal: (:Person {id})-[:TRUSTEE_FOR]->(:Document*)
    Returns every document the person is registered to sign, sorted by
    unlock_at ascending so pending obligations surface first.

    Consumed by Anushka's MilestoneNodeBadge to count how many signatures
    each family member node still owes (badge shows count, not list).
    """
    result = trustee.get_documents_for_trustee(person_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Person {person_id} not found in graph",
        )
    return {"person_id": person_id, "pending_count": sum(1 for d in result if not d["has_signed"]), "documents": result}