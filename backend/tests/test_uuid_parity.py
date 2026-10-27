import json
from pathlib import Path
from uuid import UUID
import pytest

from scripts.seed import PERSON_IDS, JOINT_FAMILY_ID, NUCLEAR_A_ID, NUCLEAR_B_ID


def test_seed_and_contract_uuid_parity():
    """
    Asserts 100% UUID parity between PostgreSQL seed script (backend/scripts/seed.py)
    and the authoritative Neo4j Tree Contract (contracts/graph-tree-response.json).
    Ensures zero ID drift between relational Postgres and graph Neo4j databases.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    contract_file = root_dir / "contracts" / "graph-tree-response.json"
    
    assert contract_file.exists(), f"Contract file not found at: {contract_file}"
    
    with open(contract_file, "r", encoding="utf-8") as f:
        contract = json.load(f)
        
    # 1. Clan ID parity
    contract_clan_id = UUID(contract["clan_id"])
    assert contract_clan_id == JOINT_FAMILY_ID, (
        f"Clan ID mismatch: {contract_clan_id} != {JOINT_FAMILY_ID}"
    )
    
    # 2. Extract node UUIDs from contract
    contract_nodes = contract["nodes"]
    assert len(contract_nodes) == 10, f"Expected 10 family members in contract, found {len(contract_nodes)}"
    
    contract_node_ids = {UUID(node["id"]) for node in contract_nodes}
    seed_person_ids = set(PERSON_IDS.values())
    
    # 3. Assert exact 1:1 set equality (Zero orphans on either side)
    missing_in_contract = seed_person_ids - contract_node_ids
    orphan_in_contract = contract_node_ids - seed_person_ids
    
    assert len(missing_in_contract) == 0, f"Seed UUIDs missing from graph contract: {missing_in_contract}"
    assert len(orphan_in_contract) == 0, f"Orphan UUIDs in graph contract not in seed: {orphan_in_contract}"
    assert contract_node_ids == seed_person_ids, "UUID parity assertion failed"
    
    # 4. Generational integrity verification across the 3 generations
    gen_map = {}
    for node in contract_nodes:
        uid = UUID(node["id"])
        gen = node["data"]["generation"]
        gen_map[uid] = gen
        
    # Gen 1 Patriarch & Matriarch
    assert gen_map[PERSON_IDS["arthur"]] == 1
    assert gen_map[PERSON_IDS["eleanor"]] == 1
    
    # Gen 2 Children & In-Laws
    assert gen_map[PERSON_IDS["david"]] == 2
    assert gen_map[PERSON_IDS["sarah"]] == 2
    assert gen_map[PERSON_IDS["michael"]] == 2
    assert gen_map[PERSON_IDS["clara"]] == 2
    assert gen_map[PERSON_IDS["robert"]] == 2
    
    # Gen 3 Grandchildren
    assert gen_map[PERSON_IDS["lucas"]] == 3
    assert gen_map[PERSON_IDS["sophia"]] == 3
    assert gen_map[PERSON_IDS["emma"]] == 3
    
    print("\n[Parity Verified] 100% UUID parity across all 10 Vance Clan personas in PostgreSQL & Neo4j.")
