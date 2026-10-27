"""
Sprint 3 deliverable (Riya + Runeet): pushes the Postgres-seeded family
data into Neo4j via graph-service's HTTP API.

Person attributes come from Runeet's dedicated sync endpoint
(GET /api/v1/users/sync/persons) -- ClanPersonSyncResponse is already
field-for-field identical to graph-service's PersonIn, so each person is
forwarded as-is with no reshaping.

Relationships (PARENT_OF / MARRIED_TO) still come from
contracts/graph-tree-response.json, NOT Postgres: FamilyMembership only
stores each person's relation_to_head string, not explicit parent/spouse
pairs, so there's nowhere else to pull them from yet. Worth a follow-up
ticket for Runeet to model real parent_id/spouse_id relationships once
this goes beyond the fixed Vance fixture.

Run AFTER `python scripts/seed.py`, with both services already running:
    # terminal 1
    cd backend && uvicorn app.main:app --port 8000
    # terminal 2
    cd graph-service && uvicorn main:app --port 8001
    # terminal 3
    cd backend && python scripts/sync_postgres_to_neo4j.py

Env vars (all optional, dev defaults match config.py):
    BACKEND_API_URL     default http://localhost:8000
    GRAPH_SERVICE_URL   default http://localhost:8001
    SERVICE_API_KEY     default "service-role-key-placeholder"
                        (matches backend's dev default -- MUST be
                        overridden with a real secret outside local dev)
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
GRAPH_SERVICE_URL = os.environ.get("GRAPH_SERVICE_URL", "http://localhost:8001")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "service-role-key-placeholder")
HEADERS = {"X-API-Key": SERVICE_API_KEY}

# backend/scripts/sync_postgres_to_neo4j.py -> repo root -> contracts/
CONTRACT_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "graph-tree-response.json"


def load_contract_edges():
    with open(CONTRACT_PATH) as f:
        contract = json.load(f)
    return contract["edges"]


async def fetch_persons(client):
    resp = await client.get(f"{BACKEND_API_URL}/api/v1/users/sync/persons", headers=HEADERS)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success", True):
        raise RuntimeError(f"Backend sync endpoint reported failure: {body}")
    return body["data"]  # APIResponse wrapper -- persons are under "data"


async def sync_persons(client, persons):
    failed = []
    for person in persons:
        try:
            resp = await client.post(f"{GRAPH_SERVICE_URL}/api/graph/person", json=person)
            resp.raise_for_status()
            print(f"  OK   {person['full_name']} ({person['person_id']})")
        except httpx.HTTPError as exc:
            failed.append((person["full_name"], str(exc)))
            print(f"  FAIL {person['full_name']} ({person['person_id']}): {exc}")
    return failed


async def sync_edges(client, edges):
    failed = []
    for edge in edges:
        label = edge["label"]
        try:
            if label == "PARENT_OF":
                resp = await client.post(
                    f"{GRAPH_SERVICE_URL}/api/graph/relationship",
                    params={"parent_id": edge["source"], "child_id": edge["target"]},
                )
            elif label == "MARRIED_TO":
                resp = await client.post(
                    f"{GRAPH_SERVICE_URL}/api/graph/relationship",
                    params={"spouse_a": edge["source"], "spouse_b": edge["target"]},
                )
            else:
                print(f"  SKIP unknown edge label {label}: {edge['id']}")
                continue
            resp.raise_for_status()
            print(f"  OK   {edge['id']}")
        except httpx.HTTPError as exc:
            failed.append((edge["id"], str(exc)))
            print(f"  FAIL {edge['id']}: {exc}")
    return failed


async def main():
    edges = load_contract_edges()

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            persons = await fetch_persons(client)
        except httpx.ConnectError:
            print(f"Could not reach backend at {BACKEND_API_URL}. "
                  f"Is `uvicorn app.main:app --port 8000` running?")
            sys.exit(2)

        if not persons:
            print(f"No persons returned from {BACKEND_API_URL}/api/v1/users/sync/persons "
                  f"-- run `python scripts/seed.py` in backend/ first.")
            sys.exit(1)

        print(f"=== Syncing {len(persons)} people: Postgres -> Neo4j ({GRAPH_SERVICE_URL}) ===")
        people_failed = await sync_persons(client, persons)

        print(f"\n=== Syncing {len(edges)} relationships "
              f"(from contracts/graph-tree-response.json -- not modeled in Postgres yet) ===")
        edges_failed = await sync_edges(client, edges)

    people_ok = len(persons) - len(people_failed)
    edges_ok = len(edges) - len(edges_failed)
    print(f"\n=== Sync complete: {people_ok}/{len(persons)} people, {edges_ok}/{len(edges)} edges ===")

    if people_failed or edges_failed:
        print(f"{len(people_failed) + len(edges_failed)} failure(s) -- see FAIL lines above.")
        sys.exit(1)

    print("Run scripts/verify_uuid_sync.py next to confirm.")


if __name__ == "__main__":
    asyncio.run(main())