import uuid
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.household import Pet, Property
from app.models.document import Document

client = TestClient(app)


# In-memory mock store for unit testing CRUD endpoints
mock_pets_db = {}
mock_properties_db = {}
mock_documents_db = {}


async def override_get_db():
    mock_session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt)

        # 1. Pets Queries
        if "FROM pets" in stmt_str:
            all_pets = list(mock_pets_db.values())
            mock_result.scalars.return_value.all.return_value = all_pets
            
            # Check for specific ID filter
            found_pet = None
            for p in all_pets:
                if str(p.id) in stmt_str:
                    found_pet = p
                    break
            mock_result.scalars.return_value.first.return_value = found_pet or (all_pets[0] if all_pets else None)
            return mock_result

        # 2. Properties Queries
        elif "FROM properties" in stmt_str:
            all_props = list(mock_properties_db.values())
            mock_result.scalars.return_value.all.return_value = all_props
            
            found_prop = None
            for pr in all_props:
                if str(pr.id) in stmt_str:
                    found_prop = pr
                    break
            mock_result.scalars.return_value.first.return_value = found_prop or (all_props[0] if all_props else None)
            return mock_result

        # 3. Documents Queries
        elif "FROM documents" in stmt_str:
            all_docs = list(mock_documents_db.values())
            mock_result.scalars.return_value.all.return_value = all_docs

            found_doc = None
            for d in all_docs:
                if str(d.id) in stmt_str:
                    found_doc = d
                    break
            mock_result.scalars.return_value.first.return_value = found_doc or (all_docs[0] if all_docs else None)
            return mock_result

        # 4. Household Members & Clan Sync Queries
        elif "family_memberships" in stmt_str:
            if "nuclear_families" in stmt_str:
                from scripts.seed import PERSON_IDS, JOINT_FAMILY_ID, NUCLEAR_A_ID, NUCLEAR_B_ID
                from datetime import date
                sync_personas = [
                    ("arthur", "Arthur Vance", "ADMIN", "HEAD", 1, "male", date(1948, 3, 15), "Patriarchal Household", NUCLEAR_A_ID),
                    ("eleanor", "Eleanor Vance", "ADMIN", "SPOUSE", 1, "female", date(1952, 8, 22), "Patriarchal Household", NUCLEAR_A_ID),
                    ("david", "David Vance", "MEMBER", "CHILD", 2, "male", date(1975, 11, 10), "Nuclear Household A", NUCLEAR_A_ID),
                    ("sarah", "Sarah Vance", "MEMBER", "SPOUSE", 2, "female", date(1978, 5, 18), "Nuclear Household A", NUCLEAR_A_ID),
                    ("michael", "Michael Vance", "MEMBER", "CHILD", 2, "male", date(1980, 2, 14), "Nuclear Household B", NUCLEAR_B_ID),
                    ("clara", "Clara Vance", "MEMBER", "SPOUSE", 2, "female", date(1982, 9, 30), "Nuclear Household B", NUCLEAR_B_ID),
                    ("robert", "Robert Vance", "MEMBER", "CHILD", 2, "male", date(1985, 7, 4), "Extended Household", NUCLEAR_A_ID),
                    ("lucas", "Lucas Vance", "CHILD", "EXTENDED", 3, "male", date(2005, 6, 12), "Nuclear Household A", NUCLEAR_A_ID),
                    ("sophia", "Sophia Vance", "CHILD", "EXTENDED", 3, "female", date(2008, 11, 20), "Nuclear Household B", NUCLEAR_B_ID),
                    ("emma", "Emma Vance", "VIEWER", "EXTENDED", 3, "female", date(2012, 1, 8), "Nuclear Household B", NUCLEAR_B_ID),
                ]
                sync_rows = []
                for key, full_name, role, rel, gen, gender, dob, nh, nfid in sync_personas:
                    u = MagicMock()
                    u.id = PERSON_IDS[key]
                    u.full_name = full_name
                    u.gender = gender
                    u.avatar_url = None
                    u.email = f"{key}@familyvault.app"
                    u.date_of_birth = dob

                    m = MagicMock()
                    m.id = uuid.uuid4()
                    m.user_id = u.id
                    m.joint_family_id = JOINT_FAMILY_ID
                    m.nuclear_family_id = nfid
                    m.role = role
                    m.relation_to_head = rel

                    jf = MagicMock()
                    jf.id = JOINT_FAMILY_ID
                    jf.name = "Vance Ancestral Clan"

                    nf = MagicMock()
                    nf.id = nfid
                    nf.household_name = nh

                    sync_rows.append((m, u, jf, nf))
                mock_result.all.return_value = sync_rows
                return mock_result

            mock_user = MagicMock()
            mock_user.id = uuid.UUID("00000000-0000-0000-0000-000000000003")
            mock_user.full_name = "David Vance"
            mock_user.gender = "male"
            mock_user.avatar_url = None
            mock_user.email = "david.vance@gmail.com"
            mock_user.date_of_birth = None

            mock_clan = MagicMock()
            mock_clan.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
            mock_clan.name = "Vance Ancestral Clan"

            mock_membership = MagicMock()
            mock_membership.id = uuid.uuid4()
            mock_membership.joint_family_id = mock_clan.id
            mock_membership.role = "HEAD"
            mock_membership.relation_to_head = "Household Head"

            mock_result.all.return_value = [(mock_membership, mock_user, mock_clan)]
            return mock_result


        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        mock_result.scalar_one_or_none.return_value = uuid.UUID("22222222-2222-2222-2222-222222222222")
        return mock_result

    def mock_add(instance):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now
        if hasattr(instance, "trustee_approvals_received") and instance.trustee_approvals_received is None:
            instance.trustee_approvals_received = []
        if hasattr(instance, "extracted_metadata") and instance.extracted_metadata is None:
            instance.extracted_metadata = {}

        if isinstance(instance, Pet):
            mock_pets_db[str(instance.id)] = instance
        elif isinstance(instance, Property):
            mock_properties_db[str(instance.id)] = instance
        elif isinstance(instance, Document):
            mock_documents_db[str(instance.id)] = instance

    async def mock_delete(instance):
        if isinstance(instance, Pet) and str(instance.id) in mock_pets_db:
            del mock_pets_db[str(instance.id)]
        elif isinstance(instance, Property) and str(instance.id) in mock_properties_db:
            del mock_properties_db[str(instance.id)]
        elif isinstance(instance, Document) and str(instance.id) in mock_documents_db:
            del mock_documents_db[str(instance.id)]

    mock_session.execute.side_effect = mock_execute
    mock_session.add = MagicMock(side_effect=mock_add)
    mock_session.delete = MagicMock(side_effect=mock_delete)
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.commit = AsyncMock()

    yield mock_session


@pytest.fixture(autouse=True)
def mock_db():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()



# ==============================================================================
# 1. PETS CRUD TESTS
# ==============================================================================

def test_pets_create_and_list():
    pet_payload = {
        "name": "Barnaby",
        "pet_type": "DOG",
        "breed": "Golden Retriever",
        "date_of_birth": "2021-04-10",
        "microchip_number": "985141002345678",
        "vaccination_schedule": [
            {"vaccine": "Rabies Booster", "administered_on": "2024-03-12", "next_due": "2025-03-12"}
        ]
    }
    # Create pet
    create_res = client.post("/api/v1/pets/", json=pet_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()["data"]
    assert created_data["name"] == "Barnaby"
    assert created_data["breed"] == "Golden Retriever"
    assert "id" in created_data
    pet_id = created_data["id"]

    # List pets
    list_res = client.get("/api/v1/pets/")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Get single pet
    get_res = client.get(f"/api/v1/pets/{pet_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Barnaby"

    # Update pet
    update_res = client.put(f"/api/v1/pets/{pet_id}", json={"breed": "Show Golden Retriever"})
    assert update_res.status_code == 200
    assert update_res.json()["data"]["breed"] == "Show Golden Retriever"

    # Delete pet
    del_res = client.delete(f"/api/v1/pets/{pet_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted_id"] == pet_id


# ==============================================================================
# 2. PROPERTIES CRUD TESTS
# ==============================================================================

def test_properties_crud():
    prop_payload = {
        "title": "Vance Ancestral Haveli & Estate",
        "property_type": "Ancestral Land & Residence",
        "survey_number": "DL-KSP-1972-88B",
        "address": "Plot 14, Civil Lines Heritage Sector, Delhi 110054",
        "estimated_valuation": 45000000.00,
        "ownership_breakdown": [
            {"user_id": "00000000-0000-0000-0000-000000000001", "share_percentage": 50},
            {"user_id": "00000000-0000-0000-0000-000000000003", "share_percentage": 50}
        ]
    }
    # Create property
    create_res = client.post("/api/v1/properties/", json=prop_payload)
    assert create_res.status_code == 201
    created_prop = create_res.json()["data"]
    assert created_prop["title"] == "Vance Ancestral Haveli & Estate"
    prop_id = created_prop["id"]

    # List properties
    list_res = client.get("/api/v1/properties/")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Get single property
    get_res = client.get(f"/api/v1/properties/{prop_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["survey_number"] == "DL-KSP-1972-88B"

    # Update valuation
    update_res = client.put(f"/api/v1/properties/{prop_id}", json={"estimated_valuation": 48000000.00})
    assert update_res.status_code == 200
    assert float(update_res.json()["data"]["estimated_valuation"]) == 48000000.00

    # Delete property
    del_res = client.delete(f"/api/v1/properties/{prop_id}")
    assert del_res.status_code == 200


# ==============================================================================
# 3. VAULT DOCUMENT & TIME CAPSULE UNLOCK TESTS
# ==============================================================================

def test_vault_document_and_time_capsule_unlock():
    doc_payload = {
        "title": "Arthur Vance Living Will & Succession Trust",
        "description": "Generational trust distribution locked until trustee approvals.",
        "category": "LEGACY_WILL",
        "visibility_tier": "PRIVATE_STRICT",
        "r2_storage_key": "vault/arthur-will.pdf",
        "file_size_bytes": 102400,
        "mime_type": "application/pdf",
        "capsule_status": "LOCKED",
        "trustee_approvals_required": 1,
        "time_capsule_unlock_at": "2030-01-01T00:00:00Z"
    }

    # Create locked document
    create_res = client.post("/api/v1/vault/", json=doc_payload)
    assert create_res.status_code == 201
    doc_data = create_res.json()["data"]
    assert doc_data["capsule_status"] == "LOCKED"
    doc_id = doc_data["id"]

    # Retrieve document
    get_res = client.get(f"/api/v1/vault/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["title"] == "Arthur Vance Living Will & Succession Trust"

    # Update metadata
    update_res = client.put(f"/api/v1/vault/{doc_id}", json={"description": "Updated trust distribution."})
    assert update_res.status_code == 200
    assert update_res.json()["data"]["description"] == "Updated trust distribution."

    # Unlock / sign-off time capsule
    unlock_res = client.patch(f"/api/v1/vault/{doc_id}/unlock", json={"trustee_notes": "Approved by Lead Admin"})
    assert unlock_res.status_code == 200
    assert unlock_res.json()["data"]["capsule_status"] == "RELEASED"

    # Delete document
    del_res = client.delete(f"/api/v1/vault/{doc_id}")
    assert del_res.status_code == 200


# ==============================================================================
# 4. HOUSEHOLD MEMBER ROSTER TESTS
# ==============================================================================

def test_household_members_roster():
    household_id = "22222222-2222-2222-2222-222222222222"
    res = client.get(f"/api/v1/users/household/{household_id}/members")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["name"] == "David Vance"
    assert data[0]["role"] == "Head"
    assert data[0]["initials"] == "DV"

    alias_res = client.get("/api/v1/household/members")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()["data"]
    assert len(alias_data) >= 1
    assert alias_data[0]["name"] == "David Vance"

