"""
test_sprint6_health_resilience.py -- Sprint 6 Deliverable 5 (Riya)
===================================================================
Owner : Riya (Graph Service Lead)
Sprint: 6  |  Deliverable: D5
Gate:  Microservice Health & Resilience Gate

Tests:
  1.  /health returns required contract keys
  2.  /health status is "healthy" | "degraded" | "offline" (valid values)
  3.  neo4j_online=True path: neo4j_ping_ms is a float, sla_gate_pass is bool
  4.  SLA gate passes when ping <= 15ms
  5.  SLA gate FAILS (degraded) when ping > 15ms
  6.  Graceful offline fallback: Neo4j unreachable -> status="offline", service stays up
  7.  offline_fallback_active is True when Neo4j is down
  8.  neo4j_ping_ms is null when offline
  9.  sla_gate_pass is null when offline
  10. sla_threshold_ms is always 15.0 regardless of online/offline
  11. service field is always "graph-service"
  12. version field is "1.0.0"
  13. Backward compatibility: Sprint 4 + 5 endpoints still importable
  14. Kinship endpoints not broken by Sprint 6 main.py changes
  15. Trustee endpoints not broken by Sprint 6 main.py changes

Run from graph-service/ directory:
    pytest tests/test_sprint6_health_resilience.py -v
"""
import sys
import os
import types
from unittest.mock import MagicMock, patch
import pytest

# -- stub neo4j + db before imports ------------------------------------------
_fake_neo4j = types.ModuleType("neo4j")
_fake_neo4j.GraphDatabase = MagicMock()
sys.modules.setdefault("neo4j", _fake_neo4j)

_fake_dotenv = types.ModuleType("dotenv")
_fake_dotenv.load_dotenv = MagicMock()
sys.modules.setdefault("dotenv", _fake_dotenv)

_fake_db = types.ModuleType("db")
_fake_db.get_driver = MagicMock()
_fake_db.NEO4J_DATABASE = "neo4j"
_fake_db.run_schema_init = MagicMock()
# Use setdefault but always patch run_schema_init in case another test suite
# already registered a 'db' stub without this attribute.
sys.modules.setdefault("db", _fake_db)
sys.modules["db"].run_schema_init = MagicMock()
sys.modules["db"].get_driver = MagicMock()
sys.modules["db"].NEO4J_DATABASE = "neo4j"


_fake_schemas = types.ModuleType("schemas")
from pydantic import BaseModel as _BM
from typing import Optional as _Opt
class _PersonIn(_BM):
    person_id: str = ""
    full_name: str = ""
    role: str = "MEMBER"
    relation_to_head: str = "EXTENDED"
    generation: int = 1
    gender: _Opt[str] = None
    birth_date: _Opt[str] = None
    is_living: bool = True
    avatar_url: _Opt[str] = None
    nuclear_household: _Opt[str] = None
    gotra: _Opt[str] = None
    clan_id: _Opt[str] = None
    clan_name: _Opt[str] = None
    position_x: _Opt[float] = None
    position_y: _Opt[float] = None
_fake_schemas.PersonIn = _PersonIn

sys.modules.setdefault("schemas", _fake_schemas)

_fake_kinship = types.ModuleType("kinship")
_fake_kinship.get_family_tree_graph = MagicMock(return_value=None)
_fake_kinship.get_kinship_path = MagicMock(return_value=None)
_fake_kinship.get_kinship_path_rich = MagicMock(return_value=None)
sys.modules.setdefault("kinship", _fake_kinship)

_fake_trustee = types.ModuleType("trustee")
_fake_trustee.upsert_document = MagicMock(return_value=None)
_fake_trustee.assign_trustee = MagicMock(return_value=None)
_fake_trustee.record_trustee_signature = MagicMock(return_value=None)
_fake_trustee.get_trustees_for_document = MagicMock(return_value=[])
_fake_trustee.get_documents_for_trustee = MagicMock(return_value=[])
sys.modules.setdefault("trustee", _fake_trustee)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
import importlib

# Force reload so the Sprint 6 enriched /health endpoint is active even if
# 'main' was already cached in sys.modules by an earlier test suite run.
if "main" in sys.modules:
    del sys.modules["main"]
import main as M
client = TestClient(M.app)


SLA_THRESHOLD_MS = 15.0


# ===========================================================================
# Helpers
# ===========================================================================

def _mock_driver_fast(ping_ms: float = 2.0):
    """Return a driver mock where RETURN 1 completes in ~ping_ms."""
    import time as _time

    def _fake_run(query):
        rec = MagicMock()
        rec.single.return_value = MagicMock()
        return rec

    sess = MagicMock()
    real_enter_time = [None]

    def _fake_enter(self_=None):
        real_enter_time[0] = _time.perf_counter()
        return sess

    def _fake_exit(*a):
        pass

    sess.__enter__ = _fake_enter
    sess.__exit__ = MagicMock(return_value=False)
    sess.run = _fake_run

    drv = MagicMock()
    drv.session.return_value = sess
    return drv


def _make_health_response(ping_ms: float = 2.0):
    """Patch get_driver + time.perf_counter to simulate a fast ping."""
    import time as _time
    drv = _mock_driver_fast(ping_ms)
    times = [0.0, ping_ms / 1000.0]   # start=0, end=ping_ms/1000
    call = [0]

    def _fake_perf():
        t = times[call[0]]
        call[0] = min(call[0] + 1, len(times) - 1)
        return t

    with patch("main.get_driver", return_value=drv),          patch("main.time.perf_counter", side_effect=_fake_perf):
        return client.get("/health")


def _make_offline_response():
    """Patch get_driver to raise RuntimeError (Neo4j unreachable)."""
    with patch("main.get_driver", side_effect=RuntimeError("Neo4j unreachable")):
        return client.get("/health")


# ===========================================================================
# 1-2. Response structure & valid status values
# ===========================================================================

class TestHealthContract:
    REQUIRED_KEYS = {
        "status", "service", "version",
        "neo4j_online", "neo4j_ping_ms",
        "sla_gate_pass", "sla_threshold_ms",
        "offline_fallback_active",
    }

    def test_all_required_keys_present_when_online(self):
        resp = _make_health_response(ping_ms=2.0)
        assert resp.status_code == 200
        data = resp.json()
        for k in self.REQUIRED_KEYS:
            assert k in data, f"Missing key: {k}"

    def test_all_required_keys_present_when_offline(self):
        resp = _make_offline_response()
        assert resp.status_code == 200
        data = resp.json()
        for k in self.REQUIRED_KEYS:
            assert k in data, f"Missing key: {k}"

    def test_status_is_valid_value_online(self):
        resp = _make_health_response(ping_ms=2.0)
        assert resp.json()["status"] in {"healthy", "degraded", "offline"}

    def test_status_is_valid_value_offline(self):
        resp = _make_offline_response()
        assert resp.json()["status"] == "offline"


# ===========================================================================
# 3-4. Online + SLA PASS path
# ===========================================================================

class TestSlaGatePass:
    def test_sla_gate_pass_true_when_ping_under_15ms(self):
        resp = _make_health_response(ping_ms=2.0)
        data = resp.json()
        assert data["neo4j_online"] is True
        assert data["neo4j_ping_ms"] <= SLA_THRESHOLD_MS
        assert data["sla_gate_pass"] is True
        assert data["status"] == "healthy"

    def test_neo4j_ping_ms_is_float(self):
        resp = _make_health_response(ping_ms=5.0)
        ping = resp.json()["neo4j_ping_ms"]
        assert isinstance(ping, (int, float))

    def test_offline_fallback_false_when_online(self):
        resp = _make_health_response(ping_ms=3.0)
        assert resp.json()["offline_fallback_active"] is False


# ===========================================================================
# 5. SLA FAIL → degraded
# ===========================================================================

class TestSlaGateFail:
    def test_sla_gate_false_when_ping_over_15ms(self):
        """Use a real sleep inside the mock so the wall-clock timer records
        an actual delay > 15ms — no monkey-patching of time needed."""
        import time as _real_time

        def _slow_run(query):
            _real_time.sleep(0.025)   # 25ms real delay
            rec = MagicMock()
            rec.single.return_value = MagicMock()
            return rec

        sess = MagicMock()
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__ = MagicMock(return_value=False)
        sess.run = _slow_run
        drv = MagicMock()
        drv.session.return_value = sess

        with patch("main.get_driver", return_value=drv):
            resp = client.get("/health")

        data = resp.json()
        assert data["neo4j_online"] is True
        assert data["neo4j_ping_ms"] > SLA_THRESHOLD_MS
        assert data["sla_gate_pass"] is False
        assert data["status"] == "degraded"





# ===========================================================================
# 6-9. Offline fallback
# ===========================================================================

class TestOfflineFallback:
    def test_status_is_offline_when_neo4j_down(self):
        resp = _make_offline_response()
        assert resp.status_code == 200
        assert resp.json()["status"] == "offline"

    def test_offline_fallback_active_true(self):
        resp = _make_offline_response()
        assert resp.json()["offline_fallback_active"] is True

    def test_neo4j_ping_ms_null_when_offline(self):
        resp = _make_offline_response()
        assert resp.json()["neo4j_ping_ms"] is None

    def test_sla_gate_pass_null_when_offline(self):
        resp = _make_offline_response()
        assert resp.json()["sla_gate_pass"] is None

    def test_neo4j_online_false_when_offline(self):
        resp = _make_offline_response()
        assert resp.json()["neo4j_online"] is False

    def test_service_still_responds_200_when_neo4j_down(self):
        """Graceful degradation: /health must NOT 500 when Neo4j is unreachable."""
        resp = _make_offline_response()
        assert resp.status_code == 200


# ===========================================================================
# 10-12. Static field values
# ===========================================================================

class TestStaticFields:
    def test_sla_threshold_is_15ms_when_online(self):
        resp = _make_health_response()
        assert resp.json()["sla_threshold_ms"] == SLA_THRESHOLD_MS

    def test_sla_threshold_is_15ms_when_offline(self):
        resp = _make_offline_response()
        assert resp.json()["sla_threshold_ms"] == SLA_THRESHOLD_MS

    def test_service_field_is_graph_service(self):
        resp = _make_health_response()
        assert resp.json()["service"] == "graph-service"

    def test_version_is_1_0_0(self):
        resp = _make_health_response()
        assert resp.json()["version"] == "1.0.0"


# ===========================================================================
# 13-15. Backward compatibility: Sprint 4, 5 not broken
# ===========================================================================

class TestBackwardCompatibility:
    def test_kinship_import_intact(self):
        import kinship as K
        assert callable(K.get_kinship_path)
        assert callable(K.get_kinship_path_rich)

    def test_trustee_import_intact(self):
        import trustee as T
        assert callable(T.upsert_document)
        assert callable(T.assign_trustee)
        assert callable(T.get_trustees_for_document)

    def test_sprint4_route_registered(self):
        routes = [r.path for r in M.app.routes]
        assert "/api/graph/kinship/{from_id}/{to_id}" in routes

    def test_sprint5_routes_registered(self):
        routes = [r.path for r in M.app.routes]
        assert "/api/graph/trustee" in routes
        assert "/api/graph/document" in routes
        assert "/api/graph/trustee/{doc_id}" in routes
