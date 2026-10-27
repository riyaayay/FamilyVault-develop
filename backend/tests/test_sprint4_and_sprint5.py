from datetime import datetime, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.media import MediaContribution
from app.models.document import Document
from app.models.user import User
from app.models.health import HealthRecord

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def test_media_inbox_and_triage_endpoints():
    mock_media_id = uuid.uuid4()
    mock_media = MediaContribution(
        id=mock_media_id,
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uploader_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        media_title="Family Reunion Lunch",
        media_type="image/jpeg",
        r2_storage_key="media/2026/reunion.jpg",
        matched_face_ids=["00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000007"],
        confidence_scores={"00000000-0000-0000-0000-000000000003": 0.95, "00000000-0000-0000-0000-000000000007": 0.78},
        status="PENDING_INBOX",
    )

    async def mock_db_media():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [mock_media]
        result.scalars.return_value.first.return_value = mock_media
        session.execute.return_value = result
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        yield session

    app.dependency_overrides[get_db] = mock_db_media

    # 1. Test GET /api/v1/media/inbox
    res = client.get("/api/v1/media/inbox")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["media_title"] == "Family Reunion Lunch"

    # 2. Test PATCH /api/v1/media/{media_id}/triage (Single Triage)
    triage_res = client.patch(
        f"/api/v1/media/{mock_media_id}/triage",
        json={"status": "AUTO_PUBLISHED"}
    )
    assert triage_res.status_code == 200
    assert triage_res.json()["data"]["status"] == "AUTO_PUBLISHED"

    # 3. Test POST /api/v1/media/batch-triage
    batch_res = client.post(
        "/api/v1/media/batch-triage",
        json={"media_ids": [str(mock_media_id)], "status": "AUTO_PUBLISHED"}
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()["data"]
    assert batch_data["processed_count"] == 1
    assert batch_data["status"] == "AUTO_PUBLISHED"

    # 4. Test GET /api/v1/media/timeline/{user_id}
    timeline_res = client.get("/api/v1/media/timeline/00000000-0000-0000-0000-000000000003")
    assert timeline_res.status_code == 200
    assert timeline_res.json()["success"] is True


def test_milestone_governance_and_badges():
    mock_doc_id = uuid.uuid4()
    mock_doc = Document(
        id=mock_doc_id,
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        nuclear_family_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        uploader_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        title="Ancestral Agricultural Land Will",
        category="WILL",
        visibility_tier="PRIVATE_STRICT",
        r2_storage_key="vault/deeds/ancestral_will.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        checksum_sha256="abc123def456",
        capsule_status="TRUSTEE_PENDING",
        trustee_approvals_required=2,
        trustee_approvals_received=["00000000-0000-0000-0000-000000000002"],
        extracted_metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def mock_db_vault():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [mock_doc]
        result.scalars.return_value.first.return_value = mock_doc
        session.execute.return_value = result
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db_vault

    # 1. Test GET /api/v1/vault/milestones/badges
    badges_res = client.get("/api/v1/vault/milestones/badges")
    assert badges_res.status_code == 200
    badges_data = badges_res.json()["data"]
    assert len(badges_data) == 1
    assert badges_data[0]["type"] == "digital_will"
    assert badges_data[0]["status"] == "SEALED"
    assert badges_data[0]["requiredSignatures"] == 2
    assert badges_data[0]["currentSignatures"] == 1

    # 2. Test POST /api/v1/vault/{doc_id}/sign (Trustee quorum completion)
    sign_res = client.post(f"/api/v1/vault/{mock_doc_id}/sign")
    assert sign_res.status_code == 200
    assert sign_res.json()["success"] is True
    assert sign_res.json()["data"]["capsule_status"] == "RELEASED"


def test_emergency_pass_and_alert_trigger():
    async def mock_db_health():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = None
        session.execute.return_value = result
        yield session

    app.dependency_overrides[get_db] = mock_db_health

    # 1. Test GET /api/v1/health/emergency-pass/eleanor-vance-24h
    pass_res = client.get("/api/v1/health/emergency-pass/eleanor-vance-24h")
    assert pass_res.status_code == 200
    pass_data = pass_res.json()["data"]
    assert pass_data["memberName"] == "Eleanor Vance"
    assert pass_data["condition"] == "Cardiac Arrhythmia / Pacemaker Active"
    assert "bloodGroup" in pass_data
    assert len(pass_data["allergies"]) > 0
    assert "signedTokenPassUrl" in pass_data
    assert "cryptographicSignature" in pass_data
    assert pass_data["isActive"] is True

    # 2. Test POST /api/v1/health/emergency-alert/trigger
    alert_res = client.post(
        "/api/v1/health/emergency-alert/trigger",
        json={"user_id": "00000000-0000-0000-0000-000000000002", "condition": "Cardiac Emergency"}
    )
    assert alert_res.status_code == 200
    alert_data = alert_res.json()["data"]
    assert alert_data["status"] == "ACTIVE_BROADCAST"
    assert alert_data["patient_id"] == "00000000-0000-0000-0000-000000000002"


def test_security_gate_privilege_escalation_guards():
    """
    Test suite directly validating Issue #38 and Deliverable 6 security gates:
    - VIEWER role cannot triage media (single or batch)
    - VIEWER role cannot inject/upload documents
    - VIEWER role cannot register properties
    - Milestone locked documents remain inaccessible to non-uploaders before unlock
    """
    from app.core.security import get_current_user, AuthenticatedUser

    viewer_user = AuthenticatedUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000010"), # Emma (VIEWER)
        email="emma@familyvault.app",
        full_name="Emma Vance",
        role="VIEWER",
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        nuclear_family_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
    )

    app.dependency_overrides[get_current_user] = lambda: viewer_user

    mock_media_id = uuid.uuid4()
    mock_media = MediaContribution(
        id=mock_media_id,
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uploader_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        media_title="Pending Triage Photo",
        media_type="image/jpeg",
        r2_storage_key="media/pending.jpg",
        status="PENDING_INBOX",
    )

    async def mock_db_sec():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [mock_media]
        result.scalars.return_value.first.return_value = mock_media
        session.execute.return_value = result
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        yield session

    app.dependency_overrides[get_db] = mock_db_sec

    # 1. VIEWER cannot triage media
    res = client.patch(f"/api/v1/media/{mock_media_id}/triage", json={"status": "AUTO_PUBLISHED"})
    assert res.status_code == 403, "Security Breach: VIEWER was able to triage media"

    # 2. VIEWER cannot batch triage media
    res = client.post("/api/v1/media/batch-triage", json={"media_ids": [str(mock_media_id)], "status": "AUTO_PUBLISHED"})
    assert res.status_code == 403, "Security Breach: VIEWER was able to batch triage media"

    # 3. VIEWER cannot inject documents
    res = client.post("/api/v1/vault/", json={
        "title": "Exploit Doc",
        "description": "Unauthorized injection attempt",
        "category": "LEGAL",
        "visibility_tier": "NUCLEAR_HOUSEHOLD",
        "r2_storage_key": "vault/exploit.pdf",
        "file_size_bytes": 1024,
        "mime_type": "application/pdf",
        "checksum_sha256": "fakehash123",
    })
    assert res.status_code == 403, "Security Breach: VIEWER was able to create document"

    # 4. VIEWER cannot create properties
    res = client.post("/api/v1/properties/", json={
        "title": "Unauthorized Villa",
        "property_type": "Residential",
        "address": "123 Exploit Way",
        "estimated_valuation": 1000000.0,
    })
    assert res.status_code == 403, "Security Breach: VIEWER was able to register property"

    # 5. Milestone locked documents cannot be read before unlock time by non-uploaders
    member_user = AuthenticatedUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000003"), # David (MEMBER)
        email="david@familyvault.app",
        full_name="David Vance",
        role="MEMBER",
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        nuclear_family_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
    )
    app.dependency_overrides[get_current_user] = lambda: member_user

    locked_doc_id = uuid.uuid4()
    locked_doc = Document(
        id=locked_doc_id,
        joint_family_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        nuclear_family_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        uploader_id=uuid.UUID("00000000-0000-0000-0000-000000000001"), # Arthur (Uploader)
        title="Living Will 2030",
        category="LEGACY_WILL",
        visibility_tier="PRIVATE_STRICT",
        r2_storage_key="vault/living_will.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        checksum_sha256="checksumwill123",
        capsule_status="LOCKED",
        time_capsule_unlock_at=datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        target_unlock_recipient_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
    )

    async def mock_db_locked():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [locked_doc]
        result.scalars.return_value.first.return_value = locked_doc
        session.execute.return_value = result
        session.flush = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db_locked

    # Non-uploader fetching individual locked document
    res = client.get(f"/api/v1/vault/{locked_doc_id}")
    assert res.status_code == 403, "Security Breach: Locked milestone capsule returned to recipient prematurely"

    # Non-uploader listing documents
    list_res = client.get("/api/v1/vault/")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 0, "Security Breach: Locked milestone document included in list"

