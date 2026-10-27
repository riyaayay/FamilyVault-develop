import asyncio
import os
import sys
 
import httpx
JOINT_FAMILY_ID = "11111111-1111-1111-1111-111111111111"
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
GRAPH_SERVICE_URL = os.environ.get("GRAPH_SERVICE_URL", "http://localhost:8001")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "service-role-key-placeholder")
HEADERS = {"X-API-Key": SERVICE_API_KEY}
 
 
async def get_postgres_person_ids(client):
    resp = await client.get(f"{BACKEND_API_URL}/api/v1/users/sync/clan/{JOINT_FAMILY_ID}/persons", headers=HEADERS)
    resp.raise_for_status()
    body = resp.json()
    return {p["person_id"] for p in body["data"]}
 
 
async def get_neo4j_person_ids(client):
    resp = await client.get(f"{GRAPH_SERVICE_URL}/api/graph/persons")
    resp.raise_for_status()
    body = resp.json()
    return {p["id"] for p in body["persons"]}
 
 
async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            postgres_ids = await get_postgres_person_ids(client)
        except httpx.ConnectError:
            print(f"Could not reach backend at {BACKEND_API_URL}. "
                  f"Is `uvicorn app.main:app --port 8000` running?")
            sys.exit(2)
 
        try:
            neo4j_ids = await get_neo4j_person_ids(client)
        except httpx.ConnectError:
            print(f"Could not reach graph-service at {GRAPH_SERVICE_URL}. "
                  f"Is `uvicorn main:app --port 8001` running?")
            sys.exit(2)
 
    missing_in_neo4j = postgres_ids - neo4j_ids
    orphaned_in_neo4j = neo4j_ids - postgres_ids
    matched = postgres_ids & neo4j_ids
 
    print("=== UUID Sync Report: Postgres users.id <-> Neo4j Person.id ===")
    print(f"Postgres persons:    {len(postgres_ids)}")
    print(f"Neo4j Person nodes:  {len(neo4j_ids)}")
    print(f"Matched:             {len(matched)}")
    print(f"Missing in Neo4j:    {len(missing_in_neo4j)}")
    print(f"Orphaned in Neo4j:   {len(orphaned_in_neo4j)}")
 
    if missing_in_neo4j:
        print("\nPostgres persons with NO matching Neo4j Person node:")
        for uid in sorted(missing_in_neo4j):
            print(f"  - {uid}")
 
    if orphaned_in_neo4j:
        print("\nNeo4j Person nodes with NO matching Postgres person:")
        for uid in sorted(orphaned_in_neo4j):
            print(f"  - {uid}")
 
    if missing_in_neo4j or orphaned_in_neo4j:
        print("\nRESULT: DRIFT DETECTED")
        sys.exit(1)
 
    print("\nRESULT: FULLY SYNCED")
    sys.exit(0)
 
 
if __name__ == "__main__":
    asyncio.run(main())