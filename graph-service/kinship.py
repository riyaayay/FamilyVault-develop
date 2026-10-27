from collections import deque

from db import get_driver, NEO4J_DATABASE

FAMILY_MEMBER_TYPE = "familyMember"

# Every field the contract's node.data object requires, with a default
# used whenever a Person node wasn't seeded with that property (e.g.
# older test data created before this schema existed).
PERSON_DATA_DEFAULTS = {
    "role": "MEMBER",
    "relation_to_head": "EXTENDED",
    "generation": 1,
    "gender": None,
    "birth_date": None,
    "is_living": True,
    "avatar_url": None,
    "nuclear_household": None,
    "gotra": None,
}

GEN_Y_BASE = 50
GEN_Y_STEP = 200
X_BASE = 200
X_STEP = 220


def _slug(full_name):
    """First-name-lowercase slug used to build readable edge ids, e.g.
    'Arthur Vance' -> 'arthur' (mirrors e_arthur_eleanor_spouse style)."""
    if not full_name:
        return "unknown"
    return full_name.strip().split()[0].lower()


def _unique_edge_id(source_slug, target_slug, rel_word, source_id, target_id, used_ids):
    """Readable id by default (e.g. e_arthur_eleanor_spouse). If two edges
    would produce the same slug -- e.g. test fixtures named 'Test Grandpa'
    / 'Test Father' / 'Test Child' all slug to 'test' -- disambiguate with
    a short fragment of the actual node ids so every edge id stays
    unique, since React Flow keys edges by id."""
    base = f"e_{source_slug}_{target_slug}_{rel_word}"
    if base not in used_ids:
        used_ids.add(base)
        return base
    disambiguated = f"{base}_{source_id[:4]}{target_id[:4]}"
    used_ids.add(disambiguated)
    return disambiguated


def _build_nodes(person_nodes):
    """Turns raw Neo4j Person nodes into contract-shaped React Flow node
    dicts, auto-laying out anyone without a stored position_x/position_y."""
    prepared = []
    for n in person_nodes:
        props = dict(n)
        data = {"full_name": props.get("full_name") or props.get("name") or "Unknown"}
        for key, default in PERSON_DATA_DEFAULTS.items():
            data[key] = props.get(key, default)
        prepared.append({
            "id": props["id"],
            "data": data,
            "generation": data["generation"],
            "pos_x": props.get("position_x"),
            "pos_y": props.get("position_y"),
            "clan_id": props.get("clan_id"),
            "clan_name": props.get("clan_name"),
        })

    by_generation = {}
    for p in prepared:
        by_generation.setdefault(p["generation"], []).append(p)

    for generation, siblings in by_generation.items():
        next_x = X_BASE
        for p in siblings:
            if p["pos_x"] is None or p["pos_y"] is None:
                p["pos_x"] = next_x
                p["pos_y"] = GEN_Y_BASE + (generation - 1) * GEN_Y_STEP
            next_x += X_STEP

    nodes = []
    name_by_id = {}
    clan_id = clan_name = None
    for p in prepared:
        name_by_id[p["id"]] = p["data"]["full_name"]
        clan_id = clan_id or p["clan_id"]
        clan_name = clan_name or p["clan_name"]
        nodes.append({
            "id": p["id"],
            "type": FAMILY_MEMBER_TYPE,
            "data": p["data"],
            "position": {"x": p["pos_x"], "y": p["pos_y"]},
        })

    return nodes, name_by_id, clan_id, clan_name


def _build_adjacency(edges):
    """Sprint 3 (Riya): shared helper for kinship classification. Reuses
    the tree's own edges list rather than re-querying Neo4j."""
    parents_of = {}    # child_id -> [parent_id, ...]
    children_of = {}   # parent_id -> [child_id, ...]
    spouses_of = {}     # person_id -> [spouse_id, ...]

    for e in edges:
        if e["label"] == "PARENT_OF":
            parents_of.setdefault(e["target"], []).append(e["source"])
            children_of.setdefault(e["source"], []).append(e["target"])
        elif e["label"] == "MARRIED_TO":
            spouses_of.setdefault(e["source"], []).append(e["target"])
            spouses_of.setdefault(e["target"], []).append(e["source"])

    return parents_of, children_of, spouses_of


def _siblings_of(person_id, parents_of, children_of):
    """Two people are treated as siblings if they share an immediate
    parent -- there's no explicit SIBLING_OF edge in the graph."""
    sibs = set()
    for parent_id in parents_of.get(person_id, []):
        for sib in children_of.get(parent_id, []):
            if sib != person_id:
                sibs.add(sib)
    return sibs


def _classify_uncle_aunt(parent_gender, target_gender, parent_dob, target_dob):
    """parent = the root's own parent; target = that parent's sibling.
    Chacha/Tauji only disambiguate by relative age on the father's side,
    per standard Hindi kinship terms -- both parties need birth_date set
    or we can't say which one is older."""
    if parent_gender == "male" and target_gender == "male":
        if parent_dob and target_dob:
            # ISO 'YYYY-MM-DD' strings compare correctly lexicographically
            return "Tauji" if target_dob < parent_dob else "Chacha"
        return "Chacha/Tauji"  # father's brother, age unknown
    if parent_gender == "male" and target_gender == "female":
        return "Bua"
    if parent_gender == "female" and target_gender == "male":
        return "Mama"
    if parent_gender == "female" and target_gender == "female":
        return "Masi"
    return None


def _bfs_hops(root_id, target_id, parents_of, children_of, spouses_of):
    """Fallback hop count for anyone the cultural-term rules below don't
    cover, walking PARENT_OF/MARRIED_TO as undirected -- same notion of
    distance as the Cypher shortestPath used by /api/graph/kinship, but
    computed from data already in hand instead of another round trip."""
    if root_id == target_id:
        return 0

    adjacency = {}

    def add_edge(a, b):
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    for child, parents in parents_of.items():
        for p in parents:
            add_edge(p, child)
    for person, sps in spouses_of.items():
        for s in sps:
            add_edge(person, s)

    visited = {root_id}
    queue = deque([(root_id, 0)])
    while queue:
        current, dist = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor == target_id:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return None


def _compute_kinship_labels(nodes, edges, root_id):
    """Sprint 3 deliverable (Riya): classifies every node's relationship
    to root_id, using Indian kinship terms (Chacha/Tauji/Mama/Bua/Masi)
    where the pattern is unambiguous, and a generic hop-based label
    otherwise. Returns {node_id: label_string}.

    NOTE: this is a first pass covering parent/child/spouse/sibling and
    father-/mother-side aunts+uncles -- it does not yet cover
    grandparents (Dada/Dadi/Nana/Nani), nieces/nephews, or cousins by
    name. Flag to Anushka before she builds display logic around this:
    the field is additive (`data.kinship_label`), so it won't break the
    existing contract, but the exact label set is still growing.
    """
    data_by_id = {n["id"]: n["data"] for n in nodes}
    parents_of, children_of, spouses_of = _build_adjacency(edges)

    root_parents = set(parents_of.get(root_id, []))
    root_children = set(children_of.get(root_id, []))
    root_spouses = set(spouses_of.get(root_id, []))
    root_siblings = _siblings_of(root_id, parents_of, children_of)

    aunts_uncles = {}  # person_id -> which of root's parents they're a sibling of
    for parent_id in root_parents:
        for sib in _siblings_of(parent_id, parents_of, children_of):
            aunts_uncles[sib] = parent_id

    labels = {}
    for node in nodes:
        pid = node["id"]
        gender = data_by_id.get(pid, {}).get("gender")

        if pid == root_id:
            labels[pid] = "self"
        elif pid in root_parents:
            labels[pid] = "father" if gender == "male" else "mother" if gender == "female" else "parent"
        elif pid in root_children:
            labels[pid] = "son" if gender == "male" else "daughter" if gender == "female" else "child"
        elif pid in root_spouses:
            labels[pid] = "spouse"
        elif pid in root_siblings:
            labels[pid] = "brother" if gender == "male" else "sister" if gender == "female" else "sibling"
        elif pid in aunts_uncles:
            parent_id = aunts_uncles[pid]
            parent_data = data_by_id.get(parent_id, {})
            labels[pid] = _classify_uncle_aunt(
                parent_data.get("gender"), gender,
                parent_data.get("birth_date"), data_by_id.get(pid, {}).get("birth_date"),
            )
        else:
            labels[pid] = None

        if labels[pid] is None and pid != root_id:
            hops = _bfs_hops(root_id, pid, parents_of, children_of, spouses_of)
            labels[pid] = _label_for_path_length(hops) if hops is not None else None

    return labels


def get_family_tree_graph(root_person_id: str, max_depth: int = 4, clan_id: str = None):
    """Builds the {endpoint, clan_id, clan_name, nodes, edges} payload for
    /api/graph/tree, matching contracts/graph-tree-response.json exactly.

    NOTE: max_depth is inlined directly into the query text (not bound as
    a parameter) because Neo4j's Cypher does not allow a parameter inside
    a variable-length path pattern (*1..$maxDepth is invalid syntax).
    max_depth is always an internal int, never raw user text, so this is
    safe. Do NOT apply this same inlining to a string parameter.

    When clan_id is given the tree is tenant-scoped: a root outside the clan
    is "not found" and relatives in other clans (e.g. an in-law's birth
    family) are dropped before edges are read.
    """
    driver = get_driver()
    max_depth = int(max_depth)

    branch_query = f"""
    MATCH (root:Person {{id: $rootId}})
    OPTIONAL MATCH (root)-[:PARENT_OF*1..{max_depth}]->(descendant:Person)
    OPTIONAL MATCH (root)<-[:PARENT_OF*1..{max_depth}]-(ancestor:Person)
    OPTIONAL MATCH (root)-[:MARRIED_TO]-(spouse:Person)
    OPTIONAL MATCH (root)<-[:PARENT_OF]-(rootParent:Person)-[:PARENT_OF]->(sibling:Person)
      WHERE sibling <> root
    OPTIONAL MATCH (root)<-[:PARENT_OF]-(parent2:Person)<-[:PARENT_OF]-(grandparent:Person)-[:PARENT_OF]->(parentSibling:Person)
      WHERE parentSibling <> parent2
    RETURN root,
           collect(DISTINCT descendant)    AS descendants,
           collect(DISTINCT ancestor)      AS ancestors,
           collect(DISTINCT spouse)        AS spouses,
           collect(DISTINCT sibling)       AS siblings,
           collect(DISTINCT parentSibling) AS auntsUncles
    """

    def _read_branch(tx):
        result = tx.run(branch_query, rootId=root_person_id)
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_read(_read_branch)

    # MATCH (root:Person {id: $rootId}) with no match returns no rows,
    # so record itself is None when the person doesn't exist.
    if record is None or record["root"] is None:
        return None

    raw_nodes = (
        [record["root"]]
        + [n for n in record["descendants"] if n is not None]
        + [n for n in record["ancestors"] if n is not None]
        + [n for n in record["spouses"] if n is not None]
        + [n for n in record["siblings"] if n is not None]
        + [n for n in record["auntsUncles"] if n is not None]
    )

    seen = set()
    unique_person_nodes = []
    for n in raw_nodes:
        pid = n["id"]
        if pid not in seen:
            seen.add(pid)
            unique_person_nodes.append(n)

    if clan_id is not None:
        if dict(record["root"]).get("clan_id") != clan_id:
            return None
        unique_person_nodes = [n for n in unique_person_nodes if dict(n).get("clan_id") == clan_id]

    ids = [n["id"] for n in unique_person_nodes]

    # Directed match returns each relationship exactly once, in whichever
    # direction it was originally MERGEd in (parent->child, or
    # spouse_a->spouse_b) -- no duplicate edges to de-dupe afterward.
    edges_query = """
    MATCH (a:Person)-[r:PARENT_OF|MARRIED_TO]->(b:Person)
    WHERE a.id IN $ids AND b.id IN $ids
    RETURN a.id AS source, b.id AS target, type(r) AS relType
    """

    def _read_edges(tx):
        result = tx.run(edges_query, ids=ids)
        return list(result)

    with driver.session(database=NEO4J_DATABASE) as session:
        edge_rows = session.execute_read(_read_edges)

    nodes, name_by_id, clan_id, clan_name = _build_nodes(unique_person_nodes)

    edges = []
    used_edge_ids = set()
    for row in edge_rows:
        rel_type = row["relType"]
        rel_word = "child" if rel_type == "PARENT_OF" else "spouse"
        source_slug = _slug(name_by_id.get(row["source"]))
        target_slug = _slug(name_by_id.get(row["target"]))
        edge_id = _unique_edge_id(
            source_slug, target_slug, rel_word, row["source"], row["target"], used_edge_ids
        )
        edge = {
            "id": edge_id,
            "source": row["source"],
            "target": row["target"],
            "label": rel_type,
            "type": "smoothstep",
        }
        if rel_type == "MARRIED_TO":
            edge["animated"] = False
        edges.append(edge)

    # Sprint 3: attach each node's cultural kinship term relative to root
    # (Chacha/Tauji/Mama/Bua/Masi where the pattern is unambiguous, else
    # a generic hop-based label). Additive field -- doesn't touch any
    # existing key the contract already defines.
    kinship_labels = _compute_kinship_labels(nodes, edges, root_person_id)
    for node in nodes:
        node["data"]["kinship_label"] = kinship_labels.get(node["id"])

    return {
        "endpoint": "GET /api/graph/tree",
        "clan_id": clan_id,
        "clan_name": clan_name,
        "nodes": nodes,
        "edges": edges,
    }


def get_kinship_path(person_a: str, person_b: str, max_depth: int = 8):
    """Shortest path (in hops) between two people through PARENT_OF or
    MARRIED_TO edges, used by /api/graph/kinship. Unaffected by the tree
    contract change above."""
    driver = get_driver()
    max_depth = int(max_depth)

    query = f"""
    MATCH (a:Person {{id: $personA}}), (b:Person {{id: $personB}})
    MATCH path = shortestPath((a)-[:PARENT_OF|MARRIED_TO*0..{max_depth}]-(b))
    RETURN length(path) AS pathLength
    """

    def _read(tx):
        result = tx.run(query, personA=person_a, personB=person_b)
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_read(_read)

    if record is None or record["pathLength"] is None:
        return None

    path_length = record["pathLength"]
    return {"pathLength": path_length, "label": _label_for_path_length(path_length)}


def _label_for_path_length(path_length: int) -> str:
    """
    Generic fallback label used when a specific cultural kinship term cannot
    be resolved from graph structure alone (e.g. distant relatives without
    known intermediate gender data).
    """
    if path_length == 0:
        return "self"
    if path_length == 1:
        return "parent/child"
    if path_length == 2:
        return "grandparent/grandchild"
    if path_length == 3:
        return "great-grandparent/great-grandchild"
    return f"distant relative ({path_length} hops)"

# ---------------------------------------------------------------------------
# Sprint 4 -- Deliverable 5 (Riya)
# GET /api/graph/kinship/{from_id}/{to_id}
# ---------------------------------------------------------------------------

def get_kinship_path_rich(from_id: str, to_id: str, max_depth: int = 8):
    """Sprint 4 D5 (Riya) -- rich kinship path endpoint.

    Returns the shortest traversal path between two family members with:
      * kinship_label   -- culturally resolved Indian kinship term where
        unambiguous (Chacha, Tauji, Mama, Bua, Masi), or a generic
        hop-based fallback.
      * path_length     -- number of hops along the shortest path.
      * path_node_ids   -- ordered list of Person UUIDs (from_id to to_id)
        used by Anushka's KinshipPathGlow component to highlight traversal
        edges on the React Flow canvas.
      * path_edges      -- ordered list of dicts:
        { source, target, rel_type: "PARENT_OF" | "MARRIED_TO" }
      * from_node / to_node -- minimal node metadata (id, full_name, gender,
        birth_date, generation) so the caller needs no separate tree fetch.

    Cultural labels re-use _compute_kinship_labels() on the path subgraph,
    giving identical behaviour to the kinship pills in the tree endpoint.

    Returns None when no path exists (caller raises 404).
    """
    driver = get_driver()
    max_depth = int(max_depth)

    # Step 1: fetch shortest path with full node + relationship data ----------
    path_query = f"""
    MATCH (a:Person {{id: $fromId}}), (b:Person {{id: $toId}})
    MATCH path = shortestPath((a)-[:PARENT_OF|MARRIED_TO*0..{max_depth}]-(b))
    WITH path,
         [n IN nodes(path) | n]            AS pathNodes,
         [r IN relationships(path) |
              {{source: startNode(r).id,
                target: endNode(r).id,
                rel_type: type(r)}}
         ]                                  AS pathRels
    RETURN
        length(path)  AS pathLength,
        pathNodes     AS pathNodes,
        pathRels      AS pathEdges
    """

    def _read_path(tx):
        result = tx.run(path_query, fromId=from_id, toId=to_id)
        return result.single()

    with driver.session(database=NEO4J_DATABASE) as session:
        record = session.execute_read(_read_path)

    if record is None or record["pathLength"] is None:
        return None

    path_length: int = record["pathLength"]
    raw_path_nodes = record["pathNodes"]
    raw_path_edges = record["pathEdges"]

    # Step 2: build minimal node objects for the sub-path --------------------
    subgraph_nodes = []
    for n in raw_path_nodes:
        props = dict(n)
        subgraph_nodes.append({
            "id": props["id"],
            "data": {
                "full_name":         props.get("full_name") or props.get("name") or "Unknown",
                "gender":            props.get("gender"),
                "birth_date":        props.get("birth_date"),
                "role":              props.get("role", "MEMBER"),
                "relation_to_head":  props.get("relation_to_head", "EXTENDED"),
                "generation":        props.get("generation", 1),
                "is_living":         props.get("is_living", True),
                "avatar_url":        props.get("avatar_url"),
                "nuclear_household": props.get("nuclear_household"),
                "gotra":             props.get("gotra"),
            },
        })

    # Build edge list for the sub-path (PARENT_OF direction preserved)
    subgraph_edges = []
    for rel in raw_path_edges:
        subgraph_edges.append({
            "source": rel["source"],
            "target": rel["target"],
            "label":  rel["rel_type"],
        })

    # Step 3: resolve cultural kinship label via Sprint 3 engine --------------
    kinship_labels = _compute_kinship_labels(subgraph_nodes, subgraph_edges, from_id)
    cultural_label = kinship_labels.get(to_id)

    # Fall back to hop-distance label if cultural term cannot be resolved
    if cultural_label is None:
        cultural_label = _label_for_path_length(path_length)

    # Step 4: ordered path_node_ids (Neo4j shortestPath already ordered) -----
    path_node_ids = [dict(n)["id"] for n in raw_path_nodes]

    # Step 5: compose response ------------------------------------------------
    from_node_data = subgraph_nodes[0]["data"] if subgraph_nodes else {}
    to_node_data   = subgraph_nodes[-1]["data"] if subgraph_nodes else {}

    return {
        "from_id":       from_id,
        "to_id":         to_id,
        "kinship_label": cultural_label,
        "path_length":   path_length,
        "path_node_ids": path_node_ids,
        "path_edges": [
            {
                "source":   e["source"],
                "target":   e["target"],
                "rel_type": e["label"],
            }
            for e in subgraph_edges
        ],
        "from_node": {"id": from_id, **from_node_data},
        "to_node":   {"id": to_id,   **to_node_data},
    }
