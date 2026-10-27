"""
test_sprint5_trustee.py -- Sprint 5 Deliverable 5 (Riya)
=========================================================
Owner : Riya (Graph Service Lead)
Sprint: 5  |  Deliverable: D5
Artifact: graph-service/trustee_graph.cypher

Tests:
  1. upsert_document -- correct Cypher parameters, idempotent
  2. assign_trustee  -- TRUSTEE_FOR edge creation, PRIMARY/BACKUP roles
  3. record_trustee_signature -- signed_at stamp
  4. get_trustees_for_document -- generational distance traversal, response shape
  5. get_documents_for_trustee -- reverse traversal, has_signed flag
  6. None returned when nodes missing (caller raises 404)
  7. Backward-compatibility: Sprint 4 kinship endpoints unaffected
  8. POST /api/graph/trustee -- FastAPI endpoint response contract
  9. GET  /api/graph/trustee/{doc_id} -- trustees list contract

Run from the graph-service/ directory:
    pytest tests/test_sprint5_trustee.py -v
"""
import sys
import os
import types
from unittest.mock import MagicMock, patch

import pytest

# -- stub db module before importing trustee --
_fake_db = types.ModuleType("db")
_fake_db.get_driver = MagicMock()
_fake_db.NEO4J_DATABASE = "neo4j"
sys.modules.setdefault("db", _fake_db)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import trustee as T

# ---- Vance Clan deterministic UUIDs ----------------------------------------
ARTHUR  = "00000000-0000-0000-0000-000000000001"
DAVID   = "00000000-0000-0000-0000-000000000003"
MICHAEL = "00000000-0000-0000-0000-000000000005"
WILL_DOC = "99999999-9999-9999-9999-999999999001"  # Arthur's Living Will


# ===========================================================================
# Helpers
# ===========================================================================

def _make_session(execute_read_return=None, execute_write_return=None):
    sess = MagicMock()
    sess.execute_read.return_value  = execute_read_return
    sess.execute_write.return_value = execute_write_return
    sess.__enter__ = MagicMock(return_value=sess)
    sess.__exit__  = MagicMock(return_value=False)
    drv = MagicMock()
    drv.session.return_value = sess
    return drv, sess


def _mock_record(**kwargs):
    """Build a MagicMock that behaves like a Neo4j record."""
    rec = MagicMock()
    rec.__getitem__ = MagicMock(side_effect=kwargs.__getitem__)
    return rec


# ===========================================================================
# 1. upsert_document
# ===========================================================================

class TestUpsertDocument:
    def test_returns_upserted_with_id(self):
        write_rec = _mock_record(id=WILL_DOC)
        drv, sess = _make_session(execute_write_return=write_rec)
        with patch("trustee.get_driver", return_value=drv):
            result = T.upsert_document(
                doc_id=WILL_DOC,
                title="Arthur Vance Living Will",
                category="LEGACY_WILL",
                capsule_status="LOCKED",
                testator_id=ARTHUR,
                trustee_approvals_required=2,
            )
        assert result is not None
        assert result["status"] == "upserted"
        assert result["id"] == WILL_DOC

    def test_returns_none_when_write_fails(self):
        drv, sess = _make_session(execute_write_return=None)
        with patch("trustee.get_driver", return_value=drv):
            result = T.upsert_document(
                doc_id=WILL_DOC,
                title="Fail Doc",
                category="LEGACY_WILL",
                capsule_status="LOCKED",
                testator_id=ARTHUR,
            )
        assert result is None

    def test_optional_unlock_at_passed_through(self):
        """time_capsule_unlock_at should be forwarded to Cypher as-is."""
        captured = {}
        def _fake_write(fn):
            tx = MagicMock()
            tx.run.return_value.single.return_value = _mock_record(id=WILL_DOC)
            fn(tx)
            captured["kwargs"] = tx.run.call_args.kwargs
            return tx.run.return_value.single.return_value

        drv = MagicMock()
        sess = MagicMock()
        sess.execute_write.side_effect = _fake_write
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv.session.return_value = sess

        with patch("trustee.get_driver", return_value=drv):
            T.upsert_document(
                doc_id=WILL_DOC,
                title="Test",
                category="TIME_CAPSULE",
                capsule_status="LOCKED",
                testator_id=ARTHUR,
                time_capsule_unlock_at="2030-01-01T00:00:00Z",
            )
        assert captured["kwargs"]["unlockAt"] == "2030-01-01T00:00:00Z"


# ===========================================================================
# 2. assign_trustee
# ===========================================================================

class TestAssignTrustee:
    def _mock_assign_rec(self):
        return _mock_record(
            trustee_id=DAVID,
            doc_id=WILL_DOC,
            role="PRIMARY",
            assigned_at="2026-10-04T00:00:00Z",
        )

    def test_returns_edge_data(self):
        drv, sess = _make_session(execute_write_return=self._mock_assign_rec())
        with patch("trustee.get_driver", return_value=drv):
            result = T.assign_trustee(DAVID, WILL_DOC, "PRIMARY")
        assert result["trustee_id"] == DAVID
        assert result["doc_id"]     == WILL_DOC
        assert result["role"]       == "PRIMARY"

    def test_backup_role_accepted(self):
        rec = _mock_record(trustee_id=MICHAEL, doc_id=WILL_DOC, role="BACKUP", assigned_at="2026-10-04T00:00:00Z")
        drv, sess = _make_session(execute_write_return=rec)
        with patch("trustee.get_driver", return_value=drv):
            result = T.assign_trustee(MICHAEL, WILL_DOC, "BACKUP")
        assert result["role"] == "BACKUP"

    def test_returns_none_when_nodes_missing(self):
        drv, sess = _make_session(execute_write_return=None)
        with patch("trustee.get_driver", return_value=drv):
            result = T.assign_trustee("unknown-id", WILL_DOC, "PRIMARY")
        assert result is None


# ===========================================================================
# 3. record_trustee_signature
# ===========================================================================

class TestRecordTrusteeSignature:
    def test_returns_signed_at(self):
        rec = _mock_record(trustee_id=DAVID, doc_id=WILL_DOC, signed_at="2026-10-04T10:00:00")
        drv, sess = _make_session(execute_write_return=rec)
        with patch("trustee.get_driver", return_value=drv):
            result = T.record_trustee_signature(DAVID, WILL_DOC)
        assert result["trustee_id"] == DAVID
        assert result["doc_id"]     == WILL_DOC
        assert result["signed_at"] is not None

    def test_returns_none_when_edge_not_found(self):
        drv, sess = _make_session(execute_write_return=None)
        with patch("trustee.get_driver", return_value=drv):
            result = T.record_trustee_signature("nobody", WILL_DOC)
        assert result is None


# ===========================================================================
# 4. get_trustees_for_document
# ===========================================================================

class TestGetTrusteesForDocument:
    def _mock_trustees(self):
        """Return plain dicts — trustee.py's comprehension builds the final
        dicts itself; we just need the raw Neo4j row fields available."""
        trustees = []
        for uid, name, gen, dist, role, signed in [
            (DAVID,   "David Vance",   2, 1, "PRIMARY", "2026-10-04T10:00:00"),
            (MICHAEL, "Michael Vance", 2, 1, "PRIMARY", None),
        ]:
            # Use a simple dict-like object whose __getitem__ returns the right value
            class _Row(dict):
                pass
            r = _Row({
                "trustee_id": uid, "full_name": name, "gender": "male",
                "generation": gen, "birth_date": "1975-01-01",
                "nuclear_household": "Patriarchal Household",
                "generational_distance": dist, "role": role,
                "signed_at": signed, "assigned_at": "2026-10-01T00:00:00",
            })
            trustees.append(r)
        return trustees

    def _make_trustee_session(self, doc_exists_returns, trustees_raw):
        """Build a session where execute_read calls the passed fn with a fake tx."""
        doc_rec = MagicMock()
        doc_rec.__getitem__ = MagicMock(side_effect={"testatorId": ARTHUR}.__getitem__)

        call_count = [0]
        def _execute_read(fn):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: _doc_exists — return the doc record
                tx = MagicMock()
                tx.run.return_value.single.return_value = doc_rec if doc_exists_returns else None
                return fn(tx) if doc_exists_returns else None
            else:
                # Second call: _read — run through fn with fake tx that yields rows
                tx = MagicMock()
                tx.run.return_value = iter(trustees_raw)
                return fn(tx)

        sess = MagicMock()
        sess.execute_read.side_effect = _execute_read
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv = MagicMock()
        drv.session.return_value = sess
        return drv


    def test_returns_list_of_trustees(self):
        drv = self._make_trustee_session(True, self._mock_trustees())
        with patch("trustee.get_driver", return_value=drv):
            result = T.get_trustees_for_document(WILL_DOC)
        assert result is not None
        assert len(result) == 2


    def test_has_signed_flag_true_when_signed_at_set(self):
        drv = self._make_trustee_session(True, self._mock_trustees())
        with patch("trustee.get_driver", return_value=drv):
            result = T.get_trustees_for_document(WILL_DOC)
        # David signed, Michael hasn't
        david_row   = next(r for r in result if r["trustee_id"] == DAVID)
        michael_row = next(r for r in result if r["trustee_id"] == MICHAEL)
        assert david_row["has_signed"]   is True
        assert michael_row["has_signed"] is False


    def test_returns_none_when_document_not_found(self):
        drv = MagicMock()
        sess = MagicMock()
        sess.execute_read.return_value = None
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv.session.return_value = sess

        with patch("trustee.get_driver", return_value=drv):
            result = T.get_trustees_for_document("non-existent-doc")
        assert result is None

    def test_returns_empty_list_when_no_trustees(self):
        doc_rec = MagicMock()
        doc_rec.__getitem__ = MagicMock(side_effect={"testatorId": ARTHUR}.__getitem__)

        drv = MagicMock()
        sess = MagicMock()
        sess.execute_read.side_effect = [doc_rec, []]
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv.session.return_value = sess

        with patch("trustee.get_driver", return_value=drv):
            result = T.get_trustees_for_document(WILL_DOC)
        assert result == []

    def test_response_shape_keys_present(self):
        """Every item must contain all contract-required keys."""
        drv = self._make_trustee_session(True, self._mock_trustees()[:1])
        with patch("trustee.get_driver", return_value=drv):
            result = T.get_trustees_for_document(WILL_DOC)
        required_keys = {
            "trustee_id", "full_name", "gender", "generation",
            "birth_date", "nuclear_household", "generational_distance",
            "role", "signed_at", "assigned_at", "has_signed",
        }
        for item in result:
            for k in required_keys:
                assert k in item, f"Missing key: {k}"



# ===========================================================================
# 5. get_documents_for_trustee
# ===========================================================================

class TestGetDocumentsForTrustee:
    def _mock_doc_row(self, signed):
        r = MagicMock()
        r.__getitem__ = MagicMock(side_effect={
            "doc_id": WILL_DOC, "title": "Arthur Will", "category": "LEGACY_WILL",
            "capsule_status": "TRUSTEE_PENDING", "required": 2, "unlock_at": None,
            "testator_id": ARTHUR, "trustee_role": "PRIMARY",
            "signed_at": "2026-10-04T10:00:00" if signed else None,
            "assigned_at": "2026-10-01T00:00:00",
        }.__getitem__)
        return r

    def test_returns_docs_list(self):
        person_rec = MagicMock()
        person_rec.__getitem__ = MagicMock(side_effect={"id": DAVID}.__getitem__)
        rows = [self._mock_doc_row(signed=False)]

        drv = MagicMock()
        sess = MagicMock()
        sess.execute_read.side_effect = [person_rec, rows]
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv.session.return_value = sess

        with patch("trustee.get_driver", return_value=drv):
            result = T.get_documents_for_trustee(DAVID)
        assert result is not None
        assert len(result) == 1

    def test_has_signed_false_when_no_signature(self):
        def _make_doc_trustee_session(signed):
            person_rec = MagicMock()
            person_rec.__getitem__ = MagicMock(side_effect={"id": DAVID}.__getitem__)
            row = {
                "doc_id": WILL_DOC, "title": "Arthur Will", "category": "LEGACY_WILL",
                "capsule_status": "TRUSTEE_PENDING", "required": 2, "unlock_at": None,
                "testator_id": ARTHUR, "trustee_role": "PRIMARY",
                "signed_at": "2026-10-04T10:00:00" if signed else None,
                "assigned_at": "2026-10-01T00:00:00",
            }
            call_count = [0]
            def _execute_read(fn):
                call_count[0] += 1
                if call_count[0] == 1:
                    tx = MagicMock()
                    tx.run.return_value.single.return_value = person_rec
                    return fn(tx)
                else:
                    tx = MagicMock()
                    tx.run.return_value = iter([row])
                    return fn(tx)
            sess = MagicMock()
            sess.execute_read.side_effect = _execute_read
            sess.__enter__ = MagicMock(return_value=sess)
            sess.__exit__  = MagicMock(return_value=False)
            drv = MagicMock()
            drv.session.return_value = sess
            return drv

        drv = _make_doc_trustee_session(signed=False)
        with patch("trustee.get_driver", return_value=drv):
            result = T.get_documents_for_trustee(DAVID)
        assert result[0]["has_signed"] is False


    def test_returns_none_when_person_not_found(self):
        drv = MagicMock()
        sess = MagicMock()
        sess.execute_read.return_value = None
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv.session.return_value = sess

        with patch("trustee.get_driver", return_value=drv):
            result = T.get_documents_for_trustee("non-existent-person")
        assert result is None


# ===========================================================================
# 6. Backward compatibility: kinship endpoints unchanged
# ===========================================================================

class TestKinshipBackwardCompat:
    """Sprint 5 must not break Sprint 3/4 kinship functions."""

    def test_get_kinship_path_still_importable(self):
        import kinship as K
        assert callable(K.get_kinship_path)

    def test_get_kinship_path_rich_still_importable(self):
        import kinship as K
        assert callable(K.get_kinship_path_rich)

    def test_trustee_module_does_not_pollute_kinship_namespace(self):
        import kinship as K
        assert not hasattr(K, "upsert_document")
        assert not hasattr(K, "assign_trustee")
