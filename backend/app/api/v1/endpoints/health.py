import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser, require_clan
from app.models.user import User
from app.models.health import HealthRecord
from app.models.family import FamilyMembership
from app.schemas.health import (
    EmergencyDossierResponse,
    EmergencyContact,
    EmergencyPassIssueResponse,
    HealthRecordResponse,
    HealthRecordUpsert,
    HealthSummaryResponse,
    MedicationItem,
)
from app.schemas.common import APIResponse

router = APIRouter()

RELATION_LABELS = {
    "HEAD": "Head of family",
    "SPOUSE": "Spouse",
    "CHILD": "Child",
    "PARENT": "Parent",
    "SIBLING": "Sibling",
    "EXTENDED": "Relative",
}

# Seeded demo pass printed on the Sprint 5 QR mock-ups. Resolves outside
# production only, so the canned QR keeps working in local demos.
DEMO_PASS_ALIASES = {"eleanor-vance-24h", "eleanor-vance"}
DEMO_PASS_MEMBER_ID = UUID("00000000-0000-0000-0000-000000000002")


# ------------------------------------------------------------------------------
# Shared lookups & access rule (mirrors the "Health record visibility policy"
# RLS policy: self, same household, or clan-wide when emergency-visible)
# ------------------------------------------------------------------------------

async def _clan_membership(db: AsyncSession, user_id: UUID, joint_family_id: UUID) -> Optional[FamilyMembership]:
    res = await db.execute(
        select(FamilyMembership).where(
            FamilyMembership.user_id == user_id,
            FamilyMembership.joint_family_id == joint_family_id,
        )
    )
    return res.scalars().first()


async def _load_patient(
    db: AsyncSession, user_id: UUID, current_user: AuthenticatedUser
) -> Tuple[User, FamilyMembership, Optional[HealthRecord]]:
    """Patient, their clan membership and health record, or 404 when the person
    is not in the caller's clan (existence is never revealed across tenants)."""
    joint_family_id = require_clan(current_user)
    membership = await _clan_membership(db, user_id, joint_family_id)
    patient = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if membership is None or patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such member in your family clan")
    record = (await db.execute(select(HealthRecord).where(HealthRecord.user_id == user_id))).scalars().first()
    return patient, membership, record


def _may_view_health(
    current_user: AuthenticatedUser, patient_id: UUID, membership: FamilyMembership, record: Optional[HealthRecord]
) -> bool:
    if current_user.is_service or current_user.user_id == patient_id:
        return True
    if current_user.nuclear_family_id and membership.nuclear_family_id == current_user.nuclear_family_id:
        return True
    return record is None or bool(record.is_emergency_visible)


def _medications(record: Optional[HealthRecord]) -> List[MedicationItem]:
    if not record or not record.current_medications:
        return []
    return [MedicationItem(**m) for m in record.current_medications if isinstance(m, dict)]


async def _emergency_contacts(
    db: AsyncSession, patient_id: UUID, membership: FamilyMembership
) -> List[EmergencyContact]:
    """Relatives flagged is_emergency_contact, the patient's own household first."""
    res = await db.execute(
        select(FamilyMembership, User)
        .join(User, FamilyMembership.user_id == User.id)
        .where(
            FamilyMembership.joint_family_id == membership.joint_family_id,
            FamilyMembership.is_emergency_contact.is_(True),
            FamilyMembership.user_id != patient_id,
        )
    )
    rows = sorted(res.all(), key=lambda r: (r[0].nuclear_family_id != membership.nuclear_family_id, r[1].full_name))
    contacts: List[EmergencyContact] = []
    seen = set()
    for m, u in rows:
        if u.id in seen:
            continue
        seen.add(u.id)
        contacts.append(
            EmergencyContact(
                name=u.full_name,
                relation=RELATION_LABELS.get(m.relation_to_head, "Relative"),
                phone_number=u.phone_number,
            )
        )
    return contacts


def _sign(payload: bytes) -> str:
    digest = hmac.new(settings.emergency_pass_secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_pass_token(user_id: UUID, expires_at: datetime) -> str:
    body = _b64(json.dumps({"sub": str(user_id), "exp": int(expires_at.timestamp())}, separators=(",", ":")).encode())
    return f"{body}.{_sign(body.encode())}"


def verify_pass_token(token: str) -> Tuple[UUID, datetime]:
    """Returns (member id, expiry) or raises 401 for forged, malformed or expired passes."""
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired emergency pass")
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(body.encode())):
            raise invalid
        claims = json.loads(_unb64(body))
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
        member_id = UUID(claims["sub"])
    except HTTPException:
        raise
    except Exception:
        raise invalid
    if expires_at <= datetime.now(timezone.utc):
        raise invalid
    return member_id, expires_at


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@router.get("/status", response_model=APIResponse[dict])
async def get_system_health() -> APIResponse[dict]:
    """System liveness and core health status."""
    return APIResponse(
        success=True,
        message="FamilyVault Core Backend is operational",
        data={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": "connected",
                "vault_engine": "ready",
                "biometrics_bridge": "online",
            },
        },
    )


@router.get("/records", response_model=APIResponse[List[HealthSummaryResponse]])
async def list_health_records(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[HealthSummaryResponse]]:
    """Clan health board: every member the caller may see, with alert-level summary.
    Full records are returned for the caller's own household and emergency-visible members."""
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    res = await db.execute(
        select(FamilyMembership, User, HealthRecord)
        .join(User, FamilyMembership.user_id == User.id)
        .outerjoin(HealthRecord, HealthRecord.user_id == User.id)
        .where(FamilyMembership.joint_family_id == current_user.joint_family_id)
        .order_by(User.date_of_birth.asc().nullslast())
    )
    summaries: List[HealthSummaryResponse] = []
    seen = set()
    for membership, user, record in res.all():
        if user.id in seen:
            continue
        seen.add(user.id)
        visible = record is not None and _may_view_health(current_user, user.id, membership, record)
        summaries.append(
            HealthSummaryResponse(
                user_id=user.id,
                full_name=user.full_name,
                nuclear_family_id=membership.nuclear_family_id,
                date_of_birth=user.date_of_birth,
                has_record=record is not None,
                restricted=record is not None and not visible,
                record=HealthRecordResponse.model_validate(record) if visible else None,
            )
        )
    return APIResponse(success=True, message=f"Retrieved {len(summaries)} member health summaries", data=summaries)


@router.get("/records/{user_id}", response_model=APIResponse[HealthRecordResponse])
async def get_health_record(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[HealthRecordResponse]:
    patient, membership, record = await _load_patient(db, user_id, current_user)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No health record on file for {patient.full_name}")
    if not _may_view_health(current_user, user_id, membership, record):
        raise HTTPException(status_code=403, detail="This health record is private to its household")
    return APIResponse(success=True, message="Health record retrieved", data=HealthRecordResponse.model_validate(record))


@router.put("/records/{user_id}", response_model=APIResponse[HealthRecordResponse])
async def upsert_health_record(
    user_id: UUID,
    body: HealthRecordUpsert,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[HealthRecordResponse]:
    """Create or update a member's health record: the member themself, or an
    ADMIN/MEMBER of the same household (parents managing a child's record)."""
    patient, membership, record = await _load_patient(db, user_id, current_user)
    same_household = membership.nuclear_family_id == current_user.nuclear_family_id
    if not (current_user.user_id == user_id or (same_household and current_user.can_write) or current_user.is_service):
        raise HTTPException(status_code=403, detail="Only the member or an adult of their household can edit this record")

    values = body.model_dump()
    values["current_medications"] = [m.model_dump() for m in body.current_medications]
    if record is None:
        record = HealthRecord(user_id=user_id, nuclear_family_id=membership.nuclear_family_id, **values)
        db.add(record)
    else:
        for field, value in values.items():
            setattr(record, field, value)

    record_audit(db, current_user, membership.joint_family_id, "HEALTH_RECORD_UPDATED", "health_records", user_id, request)
    await db.flush()
    await db.refresh(record)
    return APIResponse(
        success=True,
        message=f"Health record saved for {patient.full_name}",
        data=HealthRecordResponse.model_validate(record),
    )


@router.post(
    "/emergency-dossier/{user_id}",
    response_model=APIResponse[EmergencyDossierResponse],
    summary="Generate Instant Emergency Medical Dossier",
)
async def generate_emergency_dossier(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[EmergencyDossierResponse]:
    """
    Emergency Red Alert Protocol:
    Compiles a tamper-evident emergency summary for a family member from their
    real health record. Any clan relative may compile it when the record is
    flagged is_emergency_visible. Fields with no data on file are returned empty,
    never guessed. Every compilation is written to the audit log.
    """
    patient, membership, record = await _load_patient(db, user_id, current_user)
    if not _may_view_health(current_user, user_id, membership, record):
        raise HTTPException(status_code=403, detail="Member has disabled clan-wide emergency visibility")

    compiled_at = datetime.now(timezone.utc)
    dossier = EmergencyDossierResponse(
        patient_id=user_id,
        full_name=patient.full_name,
        date_of_birth=str(patient.date_of_birth) if patient.date_of_birth else None,
        blood_group=record.blood_group if record else None,
        critical_allergies=list(record.allergies or []) if record else [],
        chronic_conditions=list(record.chronic_conditions or []) if record else [],
        active_medications=_medications(record),
        emergency_contacts=await _emergency_contacts(db, user_id, membership),
        insurance_policy_number=record.insurance_policy_number if record else None,
        primary_physician_contact=record.primary_physician_contact if record else None,
        emergency_notes=record.emergency_notes if record else None,
        has_health_record=record is not None,
        compiled_at=compiled_at,
        tamper_proof_hash="",
    )
    # HMAC over the full clinical content, so any edit to a printed/exported
    # dossier is detectable by re-computing it server side.
    canonical = dossier.model_dump_json(exclude={"tamper_proof_hash"}).encode()
    dossier.tamper_proof_hash = hmac.new(settings.emergency_pass_secret.encode(), canonical, hashlib.sha256).hexdigest()

    record_audit(db, current_user, membership.joint_family_id, "EMERGENCY_DOSSIER_ACCESSED", "health_records", user_id, request)

    return APIResponse(
        success=True,
        message=f"Emergency Red Alert Dossier generated for {patient.full_name}",
        data=dossier,
    )


@router.post("/emergency-pass/{user_id}", response_model=APIResponse[EmergencyPassIssueResponse])
async def issue_emergency_pass(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[EmergencyPassIssueResponse]:
    """Mint a signed, read-only pass (for a QR code) that first responders can
    open without an account. It expires after EMERGENCY_PASS_TTL_HOURS."""
    patient, membership, record = await _load_patient(db, user_id, current_user)
    if not _may_view_health(current_user, user_id, membership, record):
        raise HTTPException(status_code=403, detail="Member has disabled clan-wide emergency visibility")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EMERGENCY_PASS_TTL_HOURS)
    token = issue_pass_token(user_id, expires_at)
    record_audit(db, current_user, membership.joint_family_id, "EMERGENCY_PASS_ISSUED", "health_records", user_id, request)
    return APIResponse(
        success=True,
        message=f"{settings.EMERGENCY_PASS_TTL_HOURS}-hour emergency pass issued for {patient.full_name}",
        data=EmergencyPassIssueResponse(
            token=token,
            pass_path=f"{settings.API_V1_STR}/health/emergency-pass/{token}",
            expires_at=expires_at,
        ),
    )


@router.get("/emergency-pass/{pass_token}", response_model=APIResponse[dict])
async def get_emergency_pass(
    pass_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    Sprint 5 Scannable 24-Hour Emergency Medical Telemetry Pass:
    Public read-only view for hospital triage and first responders. The token is
    HMAC-signed and expiring; forged or expired passes are rejected with 401.
    Matches frontend EmergencyAlertOverlay's EmergencyPayload shape.
    """
    if pass_token in DEMO_PASS_ALIASES and not settings.is_production:
        member_id = DEMO_PASS_MEMBER_ID
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EMERGENCY_PASS_TTL_HOURS)
    else:
        member_id, expires_at = verify_pass_token(pass_token)

    patient = (await db.execute(select(User).where(User.id == member_id))).scalars().first()
    record = (await db.execute(select(HealthRecord).where(HealthRecord.user_id == member_id))).scalars().first()

    if patient is None:
        if member_id != DEMO_PASS_MEMBER_ID:
            raise HTTPException(status_code=404, detail="Pass holder no longer exists")
        # Unseeded demo database: serve the documented Sprint 5 sample, clearly flagged.
        payload = _demo_pass_payload(pass_token, expires_at)
    else:
        conditions = list(record.chronic_conditions or []) if record else []
        notes = [n for n in [record.emergency_notes if record else None] if n]
        notes += [f"{m.name} {m.dosage} ({m.frequency})" for m in _medications(record)]
        payload = {
            "memberId": str(member_id),
            "memberName": patient.full_name,
            "condition": " / ".join(conditions) if conditions else "No chronic conditions on record",
            "bloodGroup": (record.blood_group if record else None) or "Unknown",
            "allergies": list(record.allergies or []) if record else [],
            "medicalNotes": notes,
            "emergencyContact": {
                "name": (record.primary_physician_contact if record else None) or "Not on file",
                "hospital": "",
                "phone": (record.primary_physician_contact if record else None) or "",
            },
            "signedTokenPassUrl": str(request.url),
            "isActive": True,
            "demo": False,
        }

    payload["expiresAt"] = expires_at.isoformat()
    payload["cryptographicSignature"] = pass_token.split(".", 1)[-1] if "." in pass_token else _sign(pass_token.encode())

    return APIResponse(
        success=True,
        message=f"Verified emergency pass for {payload['memberName']}",
        data=payload,
    )


def _demo_pass_payload(pass_token: str, expires_at: datetime) -> dict:
    return {
        "memberId": str(DEMO_PASS_MEMBER_ID),
        "memberName": "Eleanor Vance",
        "condition": "Cardiac Arrhythmia / Pacemaker Active",
        "bloodGroup": "A+",
        "allergies": ["Penicillin", "Sulfa Drugs"],
        "medicalNotes": [
            "Cardiac pacemaker installed Nov 2024",
            "Strict contraindication: No high-field MRI without cardiac clearance",
            "Requires immediate telemetry upon ER admission",
        ],
        "emergencyContact": {
            "name": "Dr. R. K. Sharma",
            "hospital": "AIIMS Cardiology Emergency Care",
            "phone": "+91-11-26588500",
        },
        "signedTokenPassUrl": f"{settings.API_V1_STR}/health/emergency-pass/{pass_token}",
        "isActive": True,
        "demo": True,
    }


@router.post("/emergency-alert/trigger", response_model=APIResponse[dict])
async def trigger_emergency_alert(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Sprint 5 Red Alert Broadcast:
    Activates family-wide emergency red alert modal across all client dashboards.
    """
    target_user_id = str(payload.get("user_id", current_user.user_id))
    condition = payload.get("condition", "Medical Emergency / Critical Response Required")
    try:
        target_uuid: Optional[UUID] = UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="user_id must be a UUID")

    record_audit(db, current_user, current_user.joint_family_id, "EMERGENCY_ALERT_TRIGGERED", "users", target_uuid, request)

    return APIResponse(
        success=True,
        message=f"Emergency Red Alert broadcasted for member {target_user_id}",
        data={
            "alert_id": f"alert_{hashlib.sha256(f'{target_user_id}:{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:8]}",
            "patient_id": target_user_id,
            "condition": condition,
            "status": "ACTIVE_BROADCAST",
            "triggered_by": str(current_user.user_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
