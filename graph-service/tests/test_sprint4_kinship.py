"""
test_sprint4_kinship.py -- Sprint 4 Deliverable 5 (Riya)
=========================================================
Owner : Riya (Graph Service Lead)
Sprint: 4  |  Deliverable: D5
Contract: GET /api/graph/kinship/{from_id}/{to_id}

Tests:
  1. _classify_uncle_aunt -- Chacha / Tauji / Bua / Mama / Masi
  2. _compute_kinship_labels -- offline Vance Clan benchmark
  3. get_kinship_path_rich -- response contract (mocked Neo4j)
  4. _bfs_hops -- fallback hop distance
  5. _label_for_path_length -- generic label table
  6. Backward-compatibility: get_kinship_path still returns compact shape

Run from the graph-service/ directory:
    pytest tests/test_sprint4_kinship.py -v
"""
import sys, os, types
from unittest.mock import MagicMock, patch

import pytest

# -- stub the db module before importing kinship --
_fake_db = types.ModuleType("db")
_fake_db.get_driver = MagicMock()
_fake_db.NEO4J_DATABASE = "neo4j"
sys.modules.setdefault("db", _fake_db)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import kinship as K

# ---- Vance Clan deterministic UUIDs (mirrors contracts/) -------------------
ARTHUR  = "00000000-0000-0000-0000-000000000001"
ELEANOR = "00000000-0000-0000-0000-000000000002"
DAVID   = "00000000-0000-0000-0000-000000000003"
SARAH   = "00000000-0000-0000-0000-000000000004"
MICHAEL = "00000000-0000-0000-0000-000000000005"
CLARA   = "00000000-0000-0000-0000-000000000006"
ROBERT  = "00000000-0000-0000-0000-000000000007"
LUCAS   = "00000000-0000-0000-0000-000000000008"
SOPHIA  = "00000000-0000-0000-0000-000000000009"
EMMA    = "00000000-0000-0000-0000-000000000010"

def _node(nid, full_name, gender, birth_date, generation):
    return {
        "id": nid,
        "data": {
            "full_name": full_name, "gender": gender, "birth_date": birth_date,
            "generation": generation, "role": "MEMBER",
            "relation_to_head": "EXTENDED", "is_living": True,
            "avatar_url": None, "nuclear_household": None, "gotra": None,
        },
    }

VANCE_NODES = [
    _node(ARTHUR,  "Arthur Vance",  "male",   "1948-03-15", 1),
    _node(ELEANOR, "Eleanor Vance", "female", "1952-08-22", 1),
    _node(DAVID,   "David Vance",   "male",   "1975-11-10", 2),
    _node(SARAH,   "Sarah Vance",   "female", "1978-05-18", 2),
    _node(MICHAEL, "Michael Vance", "male",   "1980-02-14", 2),
    _node(CLARA,   "Clara Vance",   "female", "1982-09-30", 2),
    _node(ROBERT,  "Robert Vance",  "male",   "1985-07-04", 2),
    _node(LUCAS,   "Lucas Vance",   "male",   "2005-06-12", 3),
    _node(SOPHIA,  "Sophia Vance",  "female", "2008-11-20", 3),
    _node(EMMA,    "Emma Vance",    "female", "2012-01-08", 3),
]

VANCE_EDGES = [
    {"source": ARTHUR,  "target": DAVID,   "label": "PARENT_OF"},
    {"source": ELEANOR, "target": DAVID,   "label": "PARENT_OF"},  # mother link
    {"source": ARTHUR,  "target": MICHAEL, "label": "PARENT_OF"},
    {"source": ELEANOR, "target": MICHAEL, "label": "PARENT_OF"},  # mother link
    {"source": ARTHUR,  "target": ROBERT,  "label": "PARENT_OF"},
    {"source": ELEANOR, "target": ROBERT,  "label": "PARENT_OF"},  # mother link
    {"source": DAVID,   "target": LUCAS,   "label": "PARENT_OF"},
    {"source": MICHAEL, "target": SOPHIA,  "label": "PARENT_OF"},
    {"source": MICHAEL, "target": EMMA,    "label": "PARENT_OF"},
    {"source": ARTHUR,  "target": ELEANOR, "label": "MARRIED_TO"},
    {"source": DAVID,   "target": SARAH,   "label": "MARRIED_TO"},
    {"source": MICHAEL, "target": CLARA,   "label": "MARRIED_TO"},
]



# ============================================================================
# 1. _classify_uncle_aunt
# ============================================================================

class TestClassifyUncleAunt:
    def test_tauji_father_elder_brother(self):
        assert K._classify_uncle_aunt("male", "male", "1975-11-10", "1970-06-01") == "Tauji"

    def test_chacha_father_younger_brother(self):
        assert K._classify_uncle_aunt("male", "male", "1975-11-10", "1980-02-14") == "Chacha"

    def test_chacha_tauji_unknown_age(self):
        assert K._classify_uncle_aunt("male", "male", None, None) == "Chacha/Tauji"

    def test_bua_fathers_sister(self):
        assert K._classify_uncle_aunt("male", "female", None, None) == "Bua"

    def test_mama_mothers_brother(self):
        assert K._classify_uncle_aunt("female", "male", None, None) == "Mama"

    def test_masi_mothers_sister(self):
        assert K._classify_uncle_aunt("female", "female", None, None) == "Masi"


# ============================================================================
# 2. _compute_kinship_labels -- offline Vance benchmark
# ============================================================================

class TestComputeKinshipLabels:
    def setup_method(self):
        self.david_labels   = K._compute_kinship_labels(VANCE_NODES, VANCE_EDGES, DAVID)
        self.lucas_labels   = K._compute_kinship_labels(VANCE_NODES, VANCE_EDGES, LUCAS)
        self.michael_labels = K._compute_kinship_labels(VANCE_NODES, VANCE_EDGES, MICHAEL)

    def test_self_label(self):
        assert self.david_labels[DAVID] == "self"

    def test_father_label(self):
        assert self.david_labels[ARTHUR] == "father"

    def test_mother_label(self):
        assert self.david_labels[ELEANOR] == "mother"

    def test_spouse_label(self):
        assert self.david_labels[SARAH] == "spouse"

    def test_son_lucas(self):
        assert self.david_labels[LUCAS] == "son"

    def test_brother_michael(self):
        assert self.david_labels[MICHAEL] == "brother"

    def test_brother_robert(self):
        assert self.david_labels[ROBERT] == "brother"

    def test_chacha_michael_from_lucas_pov(self):
        # David (1975) < Michael (1980) => Michael is younger => Chacha
        assert self.lucas_labels[MICHAEL] == "Chacha"

    def test_chacha_robert_from_lucas_pov(self):
        # David (1975) < Robert (1985) => Robert is younger => Chacha
        assert self.lucas_labels[ROBERT] == "Chacha"

    def test_clara_is_spouse_of_michael(self):
        assert self.michael_labels[CLARA] == "spouse"

    def test_sophia_is_daughter_of_michael(self):
        assert self.michael_labels[SOPHIA] == "daughter"

    def test_emma_is_daughter_of_michael(self):
        assert self.michael_labels[EMMA] == "daughter"


# ============================================================================
# 3. _bfs_hops
# ============================================================================

class TestBfsHops:
    def setup_method(self):
        self.p, self.c, self.s = K._build_adjacency(VANCE_EDGES)

    def test_self_zero(self):
        assert K._bfs_hops(DAVID, DAVID, self.p, self.c, self.s) == 0

    def test_parent_one(self):
        assert K._bfs_hops(DAVID, ARTHUR, self.p, self.c, self.s) == 1

    def test_grandparent_two(self):
        assert K._bfs_hops(LUCAS, ARTHUR, self.p, self.c, self.s) == 2

    def test_unreachable_none(self):
        stranger = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        assert K._bfs_hops(DAVID, stranger, self.p, self.c, self.s) is None


# ============================================================================
# 4. _label_for_path_length
# ============================================================================

class TestLabelForPathLength:
    def test_self(self):      assert K._label_for_path_length(0) == "self"
    def test_parent(self):    assert K._label_for_path_length(1) == "parent/child"
    def test_grand(self):     assert K._label_for_path_length(2) == "grandparent/grandchild"
    def test_great(self):     assert K._label_for_path_length(3) == "great-grandparent/great-grandchild"
    def test_distant(self):
        label = K._label_for_path_length(5)
        assert "5" in label and "distant" in label.lower()


# ============================================================================
# 5. get_kinship_path_rich -- response contract (mocked Neo4j)
# ============================================================================

def _make_node_mock(props):
    nm = MagicMock()
    nm.__iter__ = MagicMock(return_value=iter(props.items()))
    nm.keys   = MagicMock(return_value=props.keys())
    nm.values = MagicMock(return_value=props.values())
    nm.items  = MagicMock(return_value=props.items())
    nm.__getitem__ = MagicMock(side_effect=props.__getitem__)
    nm.get = MagicMock(side_effect=lambda k, d=None, p=props: p.get(k, d))
    return nm


def _run_rich(from_id, to_id, path_length, node_props_list, edge_data):
    node_mocks = [_make_node_mock(p) for p in node_props_list]

    record = MagicMock()
    record.__getitem__ = MagicMock(side_effect={
        "pathLength": path_length,
        "pathNodes":  node_mocks,
        "pathEdges":  edge_data,
    }.__getitem__)

    sess = MagicMock()
    sess.execute_read.return_value = record
    sess.__enter__ = MagicMock(return_value=sess)
    sess.__exit__  = MagicMock(return_value=False)

    drv = MagicMock()
    drv.session.return_value = sess

    with patch("kinship.get_driver", return_value=drv):
        return K.get_kinship_path_rich(from_id, to_id)


def _vp(uid, name, gender, dob, gen):
    return {
        "id": uid, "full_name": name, "gender": gender, "birth_date": dob,
        "generation": gen, "role": "MEMBER", "relation_to_head": "EXTENDED",
        "is_living": True, "avatar_url": None, "nuclear_household": None, "gotra": None,
    }


class TestGetKinshipPathRich:
    def _david_to_arthur(self):
        props = [
            _vp(DAVID,  "David Vance",  "male", "1975-11-10", 2),
            _vp(ARTHUR, "Arthur Vance", "male", "1948-03-15", 1),
        ]
        edges = [{"source": ARTHUR, "target": DAVID, "rel_type": "PARENT_OF"}]
        return _run_rich(DAVID, ARTHUR, 1, props, edges)

    def test_required_keys_present(self):
        result = self._david_to_arthur()
        for k in ("from_id","to_id","kinship_label","path_length",
                  "path_node_ids","path_edges","from_node","to_node"):
            assert k in result, f"Missing key: {k}"

    def test_path_length_value(self):
        assert self._david_to_arthur()["path_length"] == 1

    def test_from_to_ids(self):
        r = self._david_to_arthur()
        assert r["from_id"] == DAVID
        assert r["to_id"]   == ARTHUR

    def test_path_node_ids_ordered(self):
        r = self._david_to_arthur()
        assert r["path_node_ids"] == [DAVID, ARTHUR]

    def test_path_edge_rel_type(self):
        r = self._david_to_arthur()
        assert r["path_edges"][0]["rel_type"] == "PARENT_OF"

    def test_kinship_label_father(self):
        assert self._david_to_arthur()["kinship_label"] == "father"

    def test_none_when_no_path(self):
        sess = MagicMock()
        sess.execute_read.return_value = None
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv = MagicMock(); drv.session.return_value = sess
        with patch("kinship.get_driver", return_value=drv):
            assert K.get_kinship_path_rich(DAVID, "ffffffff-ffff-ffff-ffff-ffffffffffff") is None

    def test_backward_compat_get_kinship_path(self):
        """get_kinship_path (Sprint 3) must still return compact {pathLength, label}."""
        record = MagicMock()
        record.__getitem__ = MagicMock(side_effect={"pathLength": 2}.__getitem__)
        sess = MagicMock()
        sess.execute_read.return_value = record
        sess.__enter__ = MagicMock(return_value=sess)
        sess.__exit__  = MagicMock(return_value=False)
        drv = MagicMock(); drv.session.return_value = sess
        with patch("kinship.get_driver", return_value=drv):
            r = K.get_kinship_path(LUCAS, ARTHUR)
        assert "pathLength" in r and "label" in r
        assert r["pathLength"] == 2
