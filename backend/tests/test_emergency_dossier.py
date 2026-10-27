from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.family import FamilyMembership
from app.models.health import HealthRecord
from app.models.user import User

client = TestClient(app)

CLAN_ID = UUID("11111111-1111-1111-1111-111111111111")
HOUSEHOLD_ID = UUID("22222222-2222-2222-2222-222222222222")
ELEANOR_ID = UUID("00000000-0000-0000-0000-000000000002")
ARTHUR_ID = UUID("00000000-0000-0000-0000-000000000001")

eleanor = User(id=ELEANOR_ID, email="eleanor@familyvault.app", full_name="Eleanor Vance", date_of_birth=date(1952, 8, 22))
arthur = User(id=ARTHUR_ID, email="arthur@familyvault.app", full_name="Arthur Vance", phone_number="+91-98100-11001")
eleanor_membership = FamilyMembership(
    user_id=ELEANOR_ID, joint_family_id=CLAN_ID, nuclear_family_id=HOUSEHOLD_ID,
    role="ADMIN", relation_to_head="SPOUSE", is_emergency_contact=True,
)
arthur_membership = FamilyMembership(
    user_id=ARTHUR_ID, joint_family_id=CLAN_ID, nuclear_family_id=HOUSEHOLD_ID,
    role="ADMIN", relation_to_head="HEAD", is_emergency_contact=True,
)
eleanor_record = HealthRecord(
    user_id=ELEANOR_ID, nuclear_family_id=HOUSEHOLD_ID, blood_group="O+",
    allergies=["Penicillin"], chronic_conditions=["Arrhythmia"],
    current_medications=[{"name": "Amlodipine", "dosage": "5mg", "frequency": "Daily"}],
    is_emergency_visible=True,
)


def make_db(known: bool):
    """Dispatches on the table each query reads, like a tiny fake database."""
    async def execute(stmt, *args, **kwargs):
        sql = str(stmt).lower()
        res = MagicMock()
        first = None
        if "from family_memberships join users" in sql:
            res.all.return_value = [(arthur_membership, arthur)] if known else []
            return res
        if "from family_memberships" in sql:
            first = eleanor_membership if known else None
        elif "from users" in sql:
            first = eleanor if known else None
        elif "from health_records" in sql:
            first = eleanor_record if known else None
        res.scalars.return_value.first.return_value = first
        return res

    async def override():
        session = AsyncMock()
        session.execute = execute
        session.add = MagicMock()
        yield session

    return override


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_status():
    response = client.get("/api/v1/health/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


def test_emergency_dossier_compilation():
    app.dependency_overrides[get_db] = make_db(known=True)
    response = client.post(f"/api/v1/health/emergency-dossier/{ELEANOR_ID}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    dossier = res_data["data"]
    assert dossier["patient_id"] == str(ELEANOR_ID)
    assert dossier["blood_group"] == "O+"
    assert dossier["critical_allergies"] == ["Penicillin"]
    assert dossier["active_medications"][0]["name"] == "Amlodipine"
    assert [c["name"] for c in dossier["emergency_contacts"]] == ["Arthur Vance"]
    assert len(dossier["tamper_proof_hash"]) == 64


def test_emergency_dossier_never_fabricates_unknown_patients():
    app.dependency_overrides[get_db] = make_db(known=False)
    response = client.post(f"/api/v1/health/emergency-dossier/{ELEANOR_ID}")
    assert response.status_code == 404


def test_emergency_pass_round_trip_and_tamper_rejection():
    from app.api.v1.endpoints.health import issue_pass_token, verify_pass_token
    from datetime import datetime, timedelta, timezone
    from fastapi import HTTPException

    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    token = issue_pass_token(ELEANOR_ID, expires)
    member, exp = verify_pass_token(token)
    assert member == ELEANOR_ID and abs((exp - expires).total_seconds()) < 1

    body, sig = token.split(".")
    with pytest.raises(HTTPException) as forged:
        verify_pass_token(f"{body}.{sig[::-1]}")
    assert forged.value.status_code == 401

    with pytest.raises(HTTPException) as expired:
        verify_pass_token(issue_pass_token(ELEANOR_ID, datetime.now(timezone.utc) - timedelta(seconds=1)))
    assert expired.value.status_code == 401
