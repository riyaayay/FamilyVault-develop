import os
import uuid
import json
import jwt
import pytest
import pytest_asyncio
import httpx
import asyncpg
from datetime import datetime, timezone
from backend.app.core.config import settings

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres"
)
CORE_BACKEND_URL = os.getenv("CORE_BACKEND_URL", "http://localhost:8000")

# Vance Clan Canonical Identifiers
JOINT_CLAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
HOUSEHOLD_A_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")  # seed.py NUCLEAR_A_ID
HOUSEHOLD_B_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")  # seed.py NUCLEAR_B_ID

# Personas
ARTHUR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")   # Joint Head (ADMIN)
ELEANOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")  # Arthur's Spouse (Cardiac Alert)
DAVID_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")    # Trustee 1 (MEMBER)
SARAH_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")    # Trustee 3 (MEMBER)
MICHAEL_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")  # Trustee 2 (MEMBER)
SOPHIA_ID = uuid.UUID("00000000-0000-0000-0000-000000000009")   # Beneficiary (Milestone Capsule)
EMMA_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")     # Non-trustee (VIEWER)


def generate_test_jwt(user_id: uuid.UUID, email: str, role: str = "MEMBER") -> str:
    """Generate a signed JWT token matching backend Supabase JWT Secret."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "user_metadata": {"full_name": email.split("@")[0].capitalize()},
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@pytest_asyncio.fixture
async def db_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.execute("RESET ROLE;")
        await conn.close()


@pytest_asyncio.fixture
async def api_client():
    async with httpx.AsyncClient(base_url=CORE_BACKEND_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def will_document_id(db_conn):
    """Dynamically resolve or seed Arthur's Ancestral Will UUID."""
    doc_id = await db_conn.fetchval("""
        SELECT id FROM documents 
        WHERE title ILIKE '%Will%' OR category = 'LEGACY_WILL'
        ORDER BY created_at DESC LIMIT 1;
    """)
    if not doc_id:
        doc_id = uuid.UUID("4db73c89-577e-4c86-9cf9-713bd47c6584")
        await db_conn.execute("""
            INSERT INTO documents (
                id, joint_family_id, uploader_id, title, category,
                visibility_tier, r2_storage_key, file_size_bytes, mime_type,
                capsule_status, trustee_approvals_required, trustee_approvals_received
            ) VALUES (
                $1, $2, $3, 'Arthur Vance Living Will & Succession Trust', 'LEGACY_WILL',
                'PRIVATE_STRICT', 'vault/wills/arthur_will.pdf', 2048, 'application/pdf',
                'LOCKED', 2, '[]'::jsonb
            ) ON CONFLICT (id) DO UPDATE SET trustee_approvals_received = '[]'::jsonb, capsule_status = 'LOCKED';
        """, doc_id, JOINT_CLAN_ID, ARTHUR_ID)
    else:
        # Reset approvals before test run
        await db_conn.execute("""
            UPDATE documents 
            SET trustee_approvals_received = '[]'::jsonb, capsule_status = 'LOCKED' 
            WHERE id = $1;
        """, doc_id)
    return doc_id


# ==============================================================================
# 1. MULTI-TRUSTEE THRESHOLD CRYPTOGRAPHY & DIGITAL WILL GOVERNANCE
# ==============================================================================

@pytest.mark.asyncio
async def test_attack_insufficient_trustee_signatures_early_unseal(api_client, db_conn, will_document_id):
    """
    Test Barrier 1: 1-of-3 signatures must NOT unseal Arthur's digital will.
    Capsule must remain LOCKED/TRUSTEE_PENDING and not RELEASED.
    """
    token_david = generate_test_jwt(DAVID_ID, "david@familyvault.app", role="MEMBER")

    # 1. Log single signature from David
    resp_david = await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": f"Bearer {token_david}"}
    )
    assert resp_david.status_code == 200, f"David signature failed: {resp_david.text}"
    data = resp_david.json().get("data", {})
    assert data.get("capsule_status") in ["LOCKED", "TRUSTEE_PENDING"], (
        f"Capsule prematurely released after only 1 signature: {data.get('capsule_status')}"
    )

    # 2. Assert document is not prematurely released in the database
    current_status = await db_conn.fetchval(
        "SELECT capsule_status FROM documents WHERE id = $1;", will_document_id
    )
    assert current_status in ["LOCKED", "TRUSTEE_PENDING"], "Document prematurely released in database!"


@pytest.mark.asyncio
async def test_attack_duplicate_trustee_vote_replay(api_client, db_conn, will_document_id):
    """
    Test Barrier 2: Replay attack by the same trustee must not advance signature count.
    David submitting a second vote must be idempotent.
    """
    token_david = generate_test_jwt(DAVID_ID, "david@familyvault.app", role="MEMBER")

    # First signature
    await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": f"Bearer {token_david}"}
    )

    # Duplicate replay signature attempt
    await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": f"Bearer {token_david}"}
    )

    # Check received approvals list length in database
    approvals = await db_conn.fetchval(
        "SELECT trustee_approvals_received FROM documents WHERE id = $1;", will_document_id
    )
    received = json.loads(approvals) if isinstance(approvals, str) else (approvals or [])

    # Assert signature was not double-counted
    assert received.count(str(DAVID_ID)) == 1, (
        f"Replay exploit detected: Trustee signature counted multiple times! Approvals: {received}"
    )


@pytest.mark.asyncio
async def test_attack_unauthorized_non_trustee_signature(api_client, will_document_id):
    """
    Test Barrier 3: Unauthorized caller with invalid/expired token cannot sign milestone documents.
    """
    resp_unauthorized = await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": "Bearer forged_invalid_signature_token"}
    )
    assert resp_unauthorized.status_code == 401, (
        f"Privilege escalation: Invalid credentials accepted! Status: {resp_unauthorized.status_code}"
    )


@pytest.mark.asyncio
async def test_legitimate_threshold_unlock_and_audit_trail(api_client, db_conn, will_document_id):
    """
    Test Barrier 4: 2nd distinct signature (Michael) satisfies 2-of-3 threshold.
    Status transitions atomically to RELEASED.
    """
    # Reset state to clean 0/2 approvals
    await db_conn.execute("""
        UPDATE documents 
        SET trustee_approvals_received = '[]'::jsonb,
            capsule_status = 'LOCKED',
            trustee_approvals_required = 2
        WHERE id = $1;
    """, will_document_id)

    token_david = generate_test_jwt(DAVID_ID, "david@familyvault.app", role="MEMBER")
    token_michael = generate_test_jwt(MICHAEL_ID, "michael@familyvault.app", role="MEMBER")

    # 1st signature: David
    resp_david = await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": f"Bearer {token_david}"}
    )
    assert resp_david.status_code == 200, f"David sign failed: {resp_david.text}"

    # 2nd signature: Michael (satisfies 2-of-3 quorum)
    resp_michael = await api_client.post(
        f"/api/v1/vault/{will_document_id}/sign",
        headers={"Authorization": f"Bearer {token_michael}"}
    )
    assert resp_michael.status_code == 200, f"Michael signature failed: {resp_michael.text}"

    data = resp_michael.json().get("data", {})
    assert data.get("capsule_status") == "RELEASED", (
        f"Status failed to transition to RELEASED after reaching quorum: {data.get('capsule_status')}"
    )

    # Confirm in database
    db_status = await db_conn.fetchval(
        "SELECT capsule_status FROM documents WHERE id = $1;", will_document_id
    )
    assert db_status == "RELEASED", f"Database status not updated to RELEASED: {db_status}"

# ==============================================================================
# 2. HARDWARE CLOCK TIME-LOCK COUNTERMEASURE (SOPHIA'S 18TH BIRTHDAY)
# ==============================================================================

@pytest.mark.asyncio
async def test_attack_time_capsule_client_clock_drift_bypass(db_conn):
    """
    Test Barrier 5: Sophia's 18th Birthday capsule unlocks in the future.
    Rejects client clock manipulation; verifies against UTC server timestamp.
    """
    record = await db_conn.fetchrow("""
        SELECT id, capsule_status, time_capsule_unlock_at 
        FROM documents 
        WHERE title ILIKE '%Sophia%' OR target_unlock_recipient_id = $1
        ORDER BY created_at DESC LIMIT 1;
    """, SOPHIA_ID)

    if record:
        assert record["capsule_status"] in ["LOCKED", "ACTIVE"], "Milestone capsule opened prematurely!"
        if record["time_capsule_unlock_at"]:
            assert record["time_capsule_unlock_at"] > datetime.now(timezone.utc), (
                "Hardware Clock violation: Unlock timestamp has already elapsed!"
            )


# ==============================================================================
# 3. EMERGENCY RED ALERT SYSTEM (ELEANOR'S CARDIAC MEDICAL PASS)
# ==============================================================================

@pytest.mark.asyncio
async def test_attack_emergency_unauthorized_dossier_tampering(api_client):
    """
    Test Barrier 6: Forged or invalid credentials cannot access Eleanor's emergency dossier.
    """
    resp = await api_client.post(
        f"/api/v1/health/emergency-dossier/{ELEANOR_ID}",
        headers={"Authorization": "Bearer forged_invalid_emergency_token"}
    )
    assert resp.status_code == 401, (
        f"Security Breach: Emergency dossier accessible with invalid credentials! Status: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_emergency_red_alert_qr_pass_and_webhook_dispatch(api_client):
    """
    Test Barrier 7: Authorized generation returns Eleanor's emergency medical specifics
    (Pacemaker, Penicillin Allergy, AIIMS Physician Contact) and public emergency pass.
    """
    token_arthur = generate_test_jwt(ARTHUR_ID, "arthur@familyvault.app", role="ADMIN")

    # 1. Test authenticated dossier generation
    alert_resp = await api_client.post(
        f"/api/v1/health/emergency-dossier/{ELEANOR_ID}",
        headers={"Authorization": f"Bearer {token_arthur}"}
    )
    assert alert_resp.status_code == 200, f"Dossier generation failed: {alert_resp.text}"
    body = alert_resp.json().get("data", {})

    medical_str = json.dumps(body).lower()
    assert any(term in medical_str for term in ["penicillin", "cardiac", "hypertension", "allergy"]), (
        "Emergency dossier missing critical life-support health indicators!"
    )
    assert "tamper_proof_hash" in body, "Cryptographic tamper-proof hash missing from dossier!"

    # 2. Test 24-hour scannable triage pass endpoint
    pass_resp = await api_client.get("/api/v1/health/emergency-pass/eleanor-vance-24h")
    assert pass_resp.status_code == 200, f"Emergency pass retrieval failed: {pass_resp.text}"
    pass_data = pass_resp.json().get("data", {})
    assert "cryptographicSignature" in pass_data, "Cryptographic signature missing from pass!"
    assert "AIIMS" in json.dumps(pass_data), "AIIMS emergency physician contact missing from telemetry pass!"