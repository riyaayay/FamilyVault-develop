import pytest
from datetime import date
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.family import JointFamily, NuclearFamily, FamilyMembership
from app.models.user import User
from app.models.household import Pet
from scripts.seed import JOINT_FAMILY_ID, NUCLEAR_A_ID, NUCLEAR_B_ID, PERSON_IDS

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_users_sync_db():
    joint_family = JointFamily(
        id=JOINT_FAMILY_ID,
        name="Vance Ancestral Clan",
        ancestral_origin="Varanasi / Old Delhi",
        motto="Knowledge, Legacy, and Resilience",
    )
    nuclear_a = NuclearFamily(
        id=NUCLEAR_A_ID,
        joint_family_id=JOINT_FAMILY_ID,
        household_name="David & Sarah Household (Nuclear A)",
        current_city="South Delhi",
    )
    nuclear_b = NuclearFamily(
        id=NUCLEAR_B_ID,
        joint_family_id=JOINT_FAMILY_ID,
        household_name="Michael & Clara Household (Nuclear B)",
        current_city="Bengaluru",
    )
    nuclear_fams = {NUCLEAR_A_ID: nuclear_a, NUCLEAR_B_ID: nuclear_b}

    users_dict = {
        PERSON_IDS["arthur"]: User(id=PERSON_IDS["arthur"], email="arthur@familyvault.app", full_name="Arthur Vance", preferred_name="Dadaji", date_of_birth=date(1948, 3, 15), gender="male"),
        PERSON_IDS["eleanor"]: User(id=PERSON_IDS["eleanor"], email="eleanor@familyvault.app", full_name="Eleanor Vance", preferred_name="Dadiji", date_of_birth=date(1952, 8, 22), gender="female"),
        PERSON_IDS["david"]: User(id=PERSON_IDS["david"], email="david@familyvault.app", full_name="David Vance", preferred_name="David", date_of_birth=date(1975, 11, 10), gender="male"),
        PERSON_IDS["sarah"]: User(id=PERSON_IDS["sarah"], email="sarah@familyvault.app", full_name="Sarah Vance", preferred_name="Sarah", date_of_birth=date(1978, 5, 18), gender="female"),
        PERSON_IDS["michael"]: User(id=PERSON_IDS["michael"], email="michael@familyvault.app", full_name="Michael Vance", preferred_name="Mike", date_of_birth=date(1980, 2, 14), gender="male"),
        PERSON_IDS["clara"]: User(id=PERSON_IDS["clara"], email="clara@familyvault.app", full_name="Clara Vance", preferred_name="Clara", date_of_birth=date(1982, 9, 30), gender="female"),
        PERSON_IDS["robert"]: User(id=PERSON_IDS["robert"], email="robert@familyvault.app", full_name="Robert Vance", preferred_name="Rob Chacha", date_of_birth=date(1985, 7, 4), gender="male"),
        PERSON_IDS["lucas"]: User(id=PERSON_IDS["lucas"], email="lucas@familyvault.app", full_name="Lucas Vance", preferred_name="Luke", date_of_birth=date(2005, 6, 12), gender="male"),
        PERSON_IDS["sophia"]: User(id=PERSON_IDS["sophia"], email="sophia@familyvault.app", full_name="Sophia Vance", preferred_name="Soph", date_of_birth=date(2008, 11, 20), gender="female"),
        PERSON_IDS["emma"]: User(id=PERSON_IDS["emma"], email="emma@familyvault.app", full_name="Emma Vance", preferred_name="Emmy", date_of_birth=date(2012, 1, 8), gender="female"),
    }

    raw_memberships = [
        (PERSON_IDS["arthur"], NUCLEAR_A_ID, "ADMIN", "HEAD", True),
        (PERSON_IDS["eleanor"], NUCLEAR_A_ID, "ADMIN", "SPOUSE", True),
        (PERSON_IDS["david"], NUCLEAR_A_ID, "MEMBER", "CHILD", True),
        (PERSON_IDS["sarah"], NUCLEAR_A_ID, "MEMBER", "SPOUSE", True),
        (PERSON_IDS["michael"], NUCLEAR_B_ID, "MEMBER", "CHILD", True),
        (PERSON_IDS["clara"], NUCLEAR_B_ID, "MEMBER", "SPOUSE", True),
        (PERSON_IDS["robert"], NUCLEAR_A_ID, "MEMBER", "CHILD", False),
        (PERSON_IDS["lucas"], NUCLEAR_A_ID, "CHILD", "EXTENDED", False),
        (PERSON_IDS["sophia"], NUCLEAR_B_ID, "CHILD", "EXTENDED", False),
        (PERSON_IDS["emma"], NUCLEAR_B_ID, "VIEWER", "EXTENDED", False),
    ]

    memberships = []
    for idx, (uid, nid, role, rel, emerg) in enumerate(raw_memberships):
        m = FamilyMembership(
            id=UUID(f"44444444-4444-4444-4444-4444444444{idx:02d}"),
            user_id=uid,
            joint_family_id=JOINT_FAMILY_ID,
            nuclear_family_id=nid,
            role=role,
            relation_to_head=rel,
            is_emergency_contact=emerg,
        )
        memberships.append(m)

    pet = Pet(
        id=UUID("55555555-5555-5555-5555-555555555555"),
        nuclear_family_id=NUCLEAR_A_ID,
        name="Barnaby",
        pet_type="DOG",
        breed="Golden Retriever",
        date_of_birth=date(2021, 4, 10),
    )

    async def mock_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_res = MagicMock()

        # Check if querying pets
        if "pets" in stmt_str or "from pets" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [pet]
            return mock_res

        # Check if querying clan sync (ordered by date_of_birth)
        if "sync" in stmt_str or "order by" in stmt_str or ("nuclear_families" in stmt_str and "joint_families" in stmt_str):
            sorted_m = sorted(memberships, key=lambda m: users_dict[m.user_id].date_of_birth)
            rows = [
                (m, users_dict[m.user_id], joint_family, nuclear_fams[m.nuclear_family_id])
                for m in sorted_m
            ]
            mock_res.all.return_value = rows
            return mock_res

        # Querying household members
        h_rows = [
            (m, users_dict[m.user_id], joint_family)
            for m in memberships
            if m.nuclear_family_id == NUCLEAR_A_ID
        ]
        mock_res.all.return_value = h_rows
        return mock_res

    async def override_get_db():
        session = AsyncMock()
        session.execute = mock_execute
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()



def test_household_members_includes_gender_and_clan():
    """
    Riya Gap 1 & 2: Ensure HouseholdMemberResponse contains gender, clan_id, and clan_name.
    """
    response = client.get(f"/api/v1/household/{NUCLEAR_A_ID}/members")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    members = data["data"]
    assert len(members) > 0

    # Find human members
    human_members = [m for m in members if not m.get("is_pet")]
    assert len(human_members) > 0

    for m in human_members:
        # Gap 1: gender must be present
        assert "gender" in m
        assert m["gender"] in ["male", "female", "other", None]
        # Gap 2: clan fields must be present
        assert "clan_id" in m
        assert "clan_name" in m
        assert m["clan_id"] == str(JOINT_FAMILY_ID)
        assert m["clan_name"] == "Vance Ancestral Clan"
        assert "generation" in m


def test_service_role_api_key_authentication():
    """
    Riya Gap 3: Ensure scripts can authenticate via X-API-Key or Bearer token
    without requiring a live browser login session.
    """
    # 1. Test valid X-API-Key header
    headers = {"X-API-Key": "service-role-key-placeholder"}
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    me_data = resp.json()["data"]
    assert me_data["role"] == "SERVICE_ROLE"
    assert me_data["email"] == "service-sync@familyvault.app"

    # 2. Test valid Bearer service token
    bearer_headers = {"Authorization": "Bearer service-role-key-placeholder"}
    resp_bearer = client.get("/api/v1/users/me", headers=bearer_headers)
    assert resp_bearer.status_code == 200
    assert resp_bearer.json()["data"]["role"] == "SERVICE_ROLE"

    # 3. Test invalid API key is rejected
    invalid_headers = {"X-API-Key": "invalid-secret-key-12345"}
    resp_invalid = client.get("/api/v1/users/me", headers=invalid_headers)
    assert resp_invalid.status_code == 401


def test_dedicated_clan_sync_endpoint_matches_neo4j_contract():
    """
    Verify dedicated graph sync endpoint GET /api/v1/users/sync/clan/{clan_id}/persons
    returns the 10 Vance Clan personas with 1:1 schema parity for Neo4j PersonIn.
    """
    headers = {"X-API-Key": "service-role-key-placeholder"}
    url = f"/api/v1/users/sync/clan/{JOINT_FAMILY_ID}/persons"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    persons = data["data"]

    # Must contain all 10 Vance Clan seeded persons
    assert len(persons) == 10
    person_ids_received = {p["person_id"] for p in persons}
    expected_ids = {str(uid) for uid in PERSON_IDS.values()}
    assert person_ids_received == expected_ids

    # Verify Arthur Vance contract shape
    arthur = next(p for p in persons if p["person_id"] == str(PERSON_IDS["arthur"]))
    assert arthur["full_name"] == "Arthur Vance"
    assert arthur["role"] == "ADMIN"
    assert arthur["relation_to_head"] == "HEAD"
    assert arthur["generation"] == 1
    assert arthur["gender"] == "male"
    assert arthur["birth_date"] == "1948-03-15"
    assert arthur["clan_id"] == str(JOINT_FAMILY_ID)
    assert arthur["clan_name"] == "Vance Ancestral Clan"
    assert arthur["nuclear_household"] == "Patriarchal Household"

    # Verify Sophia Vance (Gen 3 granddaughter)
    sophia = next(p for p in persons if p["person_id"] == str(PERSON_IDS["sophia"]))
    assert sophia["full_name"] == "Sophia Vance"
    assert sophia["generation"] == 3
    assert sophia["gender"] == "female"
    assert sophia["clan_id"] == str(JOINT_FAMILY_ID)
