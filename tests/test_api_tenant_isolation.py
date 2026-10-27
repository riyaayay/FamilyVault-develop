"""API-level tenant isolation & governance suite.

The RLS suites prove PostgreSQL isolates tenants when queries run as the
`authenticated` role. The Core Backend, however, connects with a privileged
role, so every endpoint must enforce the same boundaries itself. These tests
exercise the HTTP API with Supabase-shaped JWTs (role claim = "authenticated",
exactly what a real browser session carries) and assert that:

* tenant + role come from family_memberships, never from JWT claims;
* a valid user from another clan sees nothing of the Vance clan;
* only designated trustees can sign a digital will;
* the emergency dossier never fabricates medical data;
* emergency passes are signed, expiring and tamper-evident.

Requires the seeded database and a running Core Backend
(see tests/README.md or the `integration` job in .github/workflows/ci.yml).
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx
import jwt
import pytest
import pytest_asyncio

from backend.app.core.config import settings

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
CORE_BACKEND_URL = os.getenv("CORE_BACKEND_URL", "http://localhost:8000")

JOINT_CLAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
HOUSEHOLD_A_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
HOUSEHOLD_B_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

ARTHUR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ELEANOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DAVID_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
MICHAEL_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")
EMMA_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
OUTSIDER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


def supabase_jwt(user_id: uuid.UUID, email: str, exp_delta: timedelta = timedelta(hours=1)) -> str:
    """A token shaped like a real Supabase access token: role is always
    'authenticated', the clan role lives only in the database."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + exp_delta,
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def auth(user_id: uuid.UUID, email: str) -> dict:
    return {"Authorization": f"Bearer {supabase_jwt(user_id, email)}"}


@pytest_asyncio.fixture
async def api():
    async with httpx.AsyncClient(base_url=CORE_BACKEND_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def clan_doc_id(db):
    return await db.fetchval(
        "SELECT id FROM documents WHERE visibility_tier = 'JOINT_CLAN' AND joint_family_id = $1 LIMIT 1",
        JOINT_CLAN_ID,
    )


@pytest_asyncio.fixture
async def will_doc_id(db):
    doc_id = await db.fetchval(
        "SELECT id FROM documents WHERE category = 'LEGACY_WILL' AND joint_family_id = $1 LIMIT 1",
        JOINT_CLAN_ID,
    )
    await db.execute(
        "UPDATE documents SET trustee_approvals_received = '[]'::jsonb, capsule_status = 'LOCKED' WHERE id = $1",
        doc_id,
    )
    return doc_id


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_resolves_tenant_and_role_from_database(api):
    res = await api.get("/api/v1/users/me", headers=auth(MICHAEL_ID, "michael@familyvault.app"))
    assert res.status_code == 200, res.text
    me = res.json()["data"]
    assert me["joint_family_id"] == str(JOINT_CLAN_ID)
    assert me["nuclear_family_id"] == str(HOUSEHOLD_B_ID)
    assert me["role"] == "MEMBER", "Clan role must come from family_memberships, not the JWT role claim"


@pytest.mark.asyncio
async def test_member_with_real_supabase_token_can_upload_to_own_household(api, db):
    res = await api.post(
        "/api/v1/vault/",
        headers=auth(DAVID_ID, "david@familyvault.app"),
        json={
            "title": "Integration Upload",
            "category": "IDENTITY",
            "visibility_tier": "NUCLEAR_HOUSEHOLD",
            "r2_storage_key": "vault/integration.pdf",
            "file_size_bytes": 10,
            "mime_type": "application/pdf",
        },
    )
    try:
        assert res.status_code == 201, res.text
        doc = res.json()["data"]
        assert doc["nuclear_family_id"] == str(HOUSEHOLD_A_ID)
        assert doc["joint_family_id"] == str(JOINT_CLAN_ID)
    finally:
        await db.execute("DELETE FROM documents WHERE title = 'Integration Upload'")


@pytest.mark.asyncio
async def test_viewer_cannot_upload_even_with_member_claim(api):
    token = jwt.encode(
        {"sub": str(EMMA_ID), "email": "emma@familyvault.app", "role": "ADMIN",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )
    res = await api.post(
        "/api/v1/vault/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Escalation", "category": "LEGAL", "visibility_tier": "JOINT_CLAN",
            "r2_storage_key": "vault/x.pdf", "file_size_bytes": 1, "mime_type": "application/pdf",
        },
    )
    assert res.status_code == 403, "A forged 'ADMIN' role claim must not override the VIEWER membership"


# ---------------------------------------------------------------------------
# Cross-clan isolation (valid token, foreign tenant)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_outsider_cannot_list_clan_vault(api):
    res = await api.get("/api/v1/vault/", headers=auth(OUTSIDER_ID, "attacker@darkweb.org"))
    assert res.status_code in (200, 403)
    if res.status_code == 200:
        assert res.json()["data"] == [], "Outsider enumerated the Vance clan vault"


@pytest.mark.asyncio
async def test_outsider_cannot_read_clan_document_by_id(api, clan_doc_id):
    res = await api.get(f"/api/v1/vault/{clan_doc_id}", headers=auth(OUTSIDER_ID, "attacker@darkweb.org"))
    assert res.status_code in (403, 404), f"Outsider read a JOINT_CLAN document: {res.status_code}"


@pytest.mark.asyncio
async def test_outsider_cannot_enumerate_users(api):
    res = await api.get("/api/v1/users/", headers=auth(OUTSIDER_ID, "attacker@darkweb.org"))
    assert res.status_code in (200, 403)
    if res.status_code == 200:
        assert res.json()["data"] == [], "Outsider enumerated clan member identities"


@pytest.mark.asyncio
async def test_outsider_cannot_compile_emergency_dossier(api):
    res = await api.post(
        f"/api/v1/health/emergency-dossier/{ELEANOR_ID}",
        headers=auth(OUTSIDER_ID, "attacker@darkweb.org"),
    )
    assert res.status_code in (403, 404), "Outsider compiled a clan member's medical dossier"


@pytest.mark.asyncio
async def test_household_document_hidden_from_other_household(api, db):
    doc_id = uuid.uuid4()
    await db.execute(
        """INSERT INTO documents (id, joint_family_id, nuclear_family_id, uploader_id, title, category,
               visibility_tier, r2_storage_key, file_size_bytes, mime_type)
           VALUES ($1, $2, $3, $4, 'Household B Tax Return', 'FINANCIAL', 'NUCLEAR_HOUSEHOLD',
                   'vault/b-tax.pdf', 1, 'application/pdf')""",
        doc_id, JOINT_CLAN_ID, HOUSEHOLD_B_ID, MICHAEL_ID,
    )
    try:
        david = await api.get(f"/api/v1/vault/{doc_id}", headers=auth(DAVID_ID, "david@familyvault.app"))
        assert david.status_code == 403
        listed = await api.get("/api/v1/vault/", headers=auth(DAVID_ID, "david@familyvault.app"))
        assert str(doc_id) not in {d["id"] for d in listed.json()["data"]}
        emma = await api.get(f"/api/v1/vault/{doc_id}", headers=auth(EMMA_ID, "emma@familyvault.app"))
        assert emma.status_code == 200, "Household B members must still see their own household records"
    finally:
        await db.execute("DELETE FROM documents WHERE id = $1", doc_id)


# ---------------------------------------------------------------------------
# Digital will governance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_trustee_signature_is_rejected(api, db, will_doc_id):
    res = await api.post(f"/api/v1/vault/{will_doc_id}/sign", headers=auth(EMMA_ID, "emma@familyvault.app"))
    assert res.status_code == 403, "A non-designated family member advanced the will's quorum"
    approvals = await db.fetchval("SELECT trustee_approvals_received FROM documents WHERE id = $1", will_doc_id)
    assert str(EMMA_ID) not in (approvals or "")


@pytest.mark.asyncio
async def test_clan_admin_cannot_force_release_someone_elses_will(api, db, will_doc_id):
    await db.execute(
        "UPDATE documents SET uploader_id = $2 WHERE id = $1", will_doc_id, ELEANOR_ID
    )
    try:
        res = await api.patch(f"/api/v1/vault/{will_doc_id}/unlock", headers=auth(ARTHUR_ID, "arthur@familyvault.app"))
        status = await db.fetchval("SELECT capsule_status FROM documents WHERE id = $1", will_doc_id)
        assert status != "RELEASED", f"Admin override released a will before its conditions (HTTP {res.status_code})"
    finally:
        await db.execute(
            "UPDATE documents SET uploader_id = $2, capsule_status = 'LOCKED' WHERE id = $1", will_doc_id, ARTHUR_ID
        )


@pytest.mark.asyncio
async def test_designated_trustee_sees_sealed_will_without_storage_key(api, will_doc_id):
    res = await api.get("/api/v1/vault/", headers=auth(MICHAEL_ID, "michael@familyvault.app"))
    assert res.status_code == 200
    sealed = [d for d in res.json()["data"] if d["id"] == str(will_doc_id)]
    assert sealed, "Trustees must be able to find the will they are asked to sign"
    assert sealed[0]["r2_storage_key"] == "", "Sealed will contents leaked to a trustee before release"


# ---------------------------------------------------------------------------
# Emergency Red Alert
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dossier_for_unknown_member_is_404_not_fabricated(api):
    res = await api.post(
        f"/api/v1/health/emergency-dossier/{uuid.uuid4()}",
        headers=auth(ARTHUR_ID, "arthur@familyvault.app"),
    )
    assert res.status_code == 404, "Dossier invented medical data for a person who does not exist"


@pytest.mark.asyncio
async def test_dossier_uses_real_record_and_writes_audit_log(api, db):
    before = await db.fetchval(
        "SELECT count(*) FROM audit_logs WHERE event_type = 'EMERGENCY_DOSSIER_ACCESSED' AND target_resource_id = $1",
        ELEANOR_ID,
    )
    res = await api.post(
        f"/api/v1/health/emergency-dossier/{ELEANOR_ID}",
        headers=auth(DAVID_ID, "david@familyvault.app"),
    )
    assert res.status_code == 200, res.text
    dossier = res.json()["data"]
    assert dossier["blood_group"] == "O+"
    assert "Penicillin" in dossier["critical_allergies"]
    contact_names = {c["name"] for c in dossier["emergency_contacts"]}
    assert "Eleanor Vance" not in contact_names, "Patient listed as their own emergency contact"
    assert "Arthur Vance" in contact_names
    after = await db.fetchval(
        "SELECT count(*) FROM audit_logs WHERE event_type = 'EMERGENCY_DOSSIER_ACCESSED' AND target_resource_id = $1",
        ELEANOR_ID,
    )
    assert after == before + 1, "Emergency access must leave an audit trail"


@pytest.mark.asyncio
async def test_emergency_pass_is_signed_expiring_and_tamper_evident(api):
    issued = await api.post(
        f"/api/v1/health/emergency-pass/{ELEANOR_ID}",
        headers=auth(DAVID_ID, "david@familyvault.app"),
    )
    assert issued.status_code == 200, issued.text
    token = issued.json()["data"]["token"]

    verified = await api.get(f"/api/v1/health/emergency-pass/{token}")
    assert verified.status_code == 200
    data = verified.json()["data"]
    assert data["memberName"] == "Eleanor Vance"
    expires = datetime.fromisoformat(data["expiresAt"])
    assert timedelta(hours=23) < expires - datetime.now(timezone.utc) <= timedelta(hours=24)

    forged = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    tampered = await api.get(f"/api/v1/health/emergency-pass/{forged}")
    assert tampered.status_code == 401, "Tampered emergency pass was accepted"
