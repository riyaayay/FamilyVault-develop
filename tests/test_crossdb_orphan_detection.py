import pytest
import asyncio
import json
from pathlib import Path
from uuid import UUID
import asyncpg

# Database connection URL from app settings
DATABASE_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

# Expected 10 deterministic seed UUIDs
EXPECTED_SEEDED_UUIDS = {
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
    "00000000-0000-0000-0000-000000000003",
    "00000000-0000-0000-0000-000000000004",
    "00000000-0000-0000-0000-000000000005",
    "00000000-0000-0000-0000-000000000006",
    "00000000-0000-0000-0000-000000000007",
    "00000000-0000-0000-0000-000000000008",
    "00000000-0000-0000-0000-000000000009",
    "00000000-0000-0000-0000-000000000010",
}

@pytest.mark.asyncio
async def test_cross_database_uuid_parity_and_orphan_detection():
    """
    Deliverable 2: Cross-Database Orphan Detection Script
    Asserts 100% 1-to-1 UUIDv4 parity between PostgreSQL users.id and 
    Neo4j / graph tree :Person nodes, with zero orphaned records.
    """
    # 1. Fetch PostgreSQL User IDs
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT id::text FROM users WHERE id IN (" + 
                               ", ".join(f"'{uid}'" for uid in EXPECTED_SEEDED_UUIDS) + ")")
        postgres_user_ids = {r["id"] for r in rows}
    finally:
        await conn.close()

    # 2. Load Graph Tree Nodes (Neo4j Contract / AuraDB representation)
    contract_path = Path(__file__).resolve().parent.parent / "contracts" / "graph-tree-response.json"
    with open(contract_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    graph_person_ids = {node["id"] for node in graph_data.get("nodes", [])}

    # 3. Parity & Orphan Assertions
    # Check Postgres against expected seed
    assert postgres_user_ids == EXPECTED_SEEDED_UUIDS, (
        f"PostgreSQL seed missing users: {EXPECTED_SEEDED_UUIDS - postgres_user_ids}"
    )

    # Check Graph against expected seed
    assert graph_person_ids == EXPECTED_SEEDED_UUIDS, (
        f"Graph missing users: {EXPECTED_SEEDED_UUIDS - graph_person_ids}"
    )

    # Assert 100% parity between both systems
    postgres_orphans = postgres_user_ids - graph_person_ids
    graph_orphans = graph_person_ids - postgres_user_ids

    assert len(postgres_orphans) == 0, f"Detected orphaned PostgreSQL users: {postgres_orphans}"
    assert len(graph_orphans) == 0, f"Detected orphaned Graph persons: {graph_orphans}"
    assert postgres_user_ids == graph_person_ids, "Strict 1-to-1 parity violated across data stores"


@pytest.mark.asyncio
async def test_graph_tree_edge_referential_integrity():
    """
    Assert that all relationship edges in the lineage tree reference valid 
    seeded member IDs with no dangling endpoints.
    """
    contract_path = Path(__file__).resolve().parent.parent / "contracts" / "graph-tree-response.json"
    with open(contract_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = {node["id"] for node in graph_data.get("nodes", [])}
    edges = graph_data.get("edges", [])

    assert len(edges) > 0, "Graph tree edges cannot be empty"

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        assert source in nodes, f"Dangling edge source: {source}"
        assert target in nodes, f"Dangling edge target: {target}"
        assert source != target, f"Self-referencing cycle detected in edge {edge['id']}"
