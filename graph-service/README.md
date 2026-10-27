# Graph Service

**Owner:** Riya  
**Stack:** Neo4j AuraDB, Cypher, FastAPI / Python  

## Responsibilities
- Provision Neo4j AuraDB instance.
- Maintain Cypher schema and constraints for `(:Person)`.
- **UUID Invariant**: Ensure all `Person.id` values strictly match PostgreSQL `users.id` (UUID format) from [contracts/schema.sql](../contracts/schema.sql).
- Implement cultural kinship resolution (Chacha, Mama, Bua, Gotra) and biological paradox validation.
- Publish and maintain [contracts/graph-tree-response.json](../contracts/graph-tree-response.json) to unblock frontend tree canvas development.

## Getting Started
Refer to [docs/COLLABORATION_PROTOCOL.md](../docs/COLLABORATION_PROTOCOL.md) for branch naming (`feature/riya-*`) and PR conventions.

## Sprint 1 Status (completed)
- `init_schema.cypher` — Person.id uniqueness constraint (matches users.id from Postgres)
- `db.py` — shared Neo4j driver + schema init runner
- `main.py` — FastAPI app, runs schema init on startup, exposes `/health`

## Run locally
cd graph-service
pip install -r requirements.txt
cp .env.example .env # fill in real AuraDB credentials
uvicorn main:app --reload --port 8001

Visit `http://localhost:8001/health` — should return `{"status": "ok", ...}` if Neo4j credentials are correct.

Append:

markdown
## Sprint 2 Status (completed)
- `kinship.py` — shortestPath kinship resolution + family branch builder
- `main.py` — added `/api/graph/tree`, `/api/graph/kinship`, `/api/graph/person`, `/api/graph/relationship`
- `contracts/graph-tree-response.json` — published contract for Anushka's tree UI

## Test locally

curl "http://localhost:8001/api/graph/tree?person_id=<some-uuid>"
curl "http://localhost:8001/api/graph/kinship?person_a=<uuid1>&person_b=<uuid2>"


## Sprint 3 (Riya)
- Verify UUID sync with Runeet against all 10 seeded users
- Support for joint-family-head recursive endpoints