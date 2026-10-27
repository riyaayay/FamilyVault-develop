"""Tenant scoping & auth for the graph service (report 3.3.3: Neo4j queries
must be clan-scoped explicitly because RLS does not protect the graph)."""

import os
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Same stubbing convention as the other suites: no live Neo4j needed.
_fake_db = types.ModuleType("db")
sys.modules.setdefault("db", _fake_db)
for _name, _value in {
    "run_schema_init": MagicMock(),
    "get_driver": MagicMock(),
    "NEO4J_DATABASE": "neo4j",
    "close_driver": MagicMock(),
}.items():
    if not hasattr(sys.modules["db"], _name):
        setattr(sys.modules["db"], _name, _value)

from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)

VANCE = "11111111-1111-1111-1111-111111111111"
LUCAS = "00000000-0000-0000-0000-000000000008"
ROBERT = "00000000-0000-0000-0000-000000000007"
SECRET = "test-secret-for-graph-service-32-bytes!!"

RICH = {
    "from_id": LUCAS,
    "to_id": ROBERT,
    "kinship_label": "Chacha",
    "path_length": 3,
    "path_node_ids": [LUCAS, "d", "a", ROBERT],
    "path_edges": [],
    "from_node": {"id": LUCAS, "generation": 3, "gotra": "Vance-Kashyap"},
    "to_node": {"id": ROBERT, "generation": 2, "gotra": None},
}


def token(sub: str) -> str:
    return jwt.encode(
        {"sub": sub, "role": "authenticated", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def jwt_mode(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_MODE", "jwt")
    monkeypatch.setattr(auth, "JWT_SECRET", SECRET)
    monkeypatch.setattr(auth, "SERVICE_KEY", "sync-key")


def test_cultural_endpoint_matches_frontend_contract():
    with patch.object(main.kinship, "get_kinship_path_rich", return_value=RICH):
        res = client.get(f"/api/graph/kinship/cultural/{LUCAS}/{ROBERT}")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "term": "Chacha",
        "english": "Father's younger brother",
        "generational_depth": 1,
        "gotra": "Vance-Kashyap",
        "path_node_ids": RICH["path_node_ids"],
    }


def test_tree_passes_explicit_clan_scope_to_query():
    with patch.object(main.kinship, "get_family_tree_graph", return_value={"nodes": [], "edges": []}) as tree:
        client.get(f"/api/graph/tree?person_id={LUCAS}&clan_id={VANCE}")
    assert tree.call_args.kwargs["clan_id"] == VANCE


def test_jwt_mode_rejects_anonymous_reads(jwt_mode):
    res = client.get(f"/api/graph/tree?person_id={LUCAS}")
    assert res.status_code == 401


def test_jwt_mode_scopes_reads_to_callers_own_clan(jwt_mode):
    with patch.object(auth, "_clan_of", return_value=VANCE), patch.object(
        main.kinship, "get_family_tree_graph", return_value={"nodes": [], "edges": []}
    ) as tree:
        res = client.get(f"/api/graph/tree?person_id={LUCAS}", headers={"Authorization": f"Bearer {token(LUCAS)}"})
    assert res.status_code == 200
    assert tree.call_args.kwargs["clan_id"] == VANCE


def test_jwt_mode_cannot_request_another_clan(jwt_mode):
    with patch.object(auth, "_clan_of", return_value=VANCE):
        res = client.get(
            f"/api/graph/tree?person_id={LUCAS}&clan_id=99999999-9999-9999-9999-999999999999",
            headers={"Authorization": f"Bearer {token(LUCAS)}"},
        )
    assert res.status_code == 404


def test_jwt_mode_rejects_forged_tokens(jwt_mode):
    forged = jwt.encode({"sub": LUCAS}, "attacker-secret-that-is-long-enough!!", algorithm="HS256")
    res = client.get(f"/api/graph/tree?person_id={LUCAS}", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_jwt_mode_writes_need_service_key(jwt_mode):
    body = {"person_id": LUCAS, "full_name": "Lucas Vance"}
    assert client.post("/api/graph/person", json=body, headers={"Authorization": f"Bearer {token(LUCAS)}"}).status_code == 401
    with patch.object(main, "get_driver") as drv:
        drv.return_value.session.return_value.__enter__.return_value.execute_write.return_value = {"id": LUCAS}
        res = client.post("/api/graph/person", json=body, headers={"X-API-Key": "sync-key"})
    assert res.status_code != 401
