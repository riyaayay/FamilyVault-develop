from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser, require_clan, require_writer
from app.models.document import Document
from app.models.family import FamilyMembership, NuclearFamily
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    TimeCapsuleUnlockRequest,
    TrusteeDesignationRequest,
)
from app.schemas.common import APIResponse

router = APIRouter()

SEALED_STATUSES = ("LOCKED", "TRUSTEE_PENDING")


# ------------------------------------------------------------------------------
# Access rules. These mirror the "Document access policy" RLS policy in
# contracts/schema.sql: the API connects with a privileged role, so it must
# enforce the same three tiers itself.
# ------------------------------------------------------------------------------

def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _trustee_ids(doc: Document) -> set:
    return {str(t) for t in (doc.designated_trustee_ids or [])}


def _is_sealed(doc: Document, now: datetime) -> bool:
    """Milestone-locked and the unlock date (if any) has not yet passed."""
    if doc.capsule_status not in SEALED_STATUSES:
        return False
    unlock_at = _as_utc(doc.time_capsule_unlock_at)
    return unlock_at is None or unlock_at > now


def _tier_allows(doc: Document, user: AuthenticatedUser) -> bool:
    if doc.visibility_tier == "JOINT_CLAN":
        return True
    if doc.visibility_tier == "NUCLEAR_HOUSEHOLD":
        return doc.nuclear_family_id is not None and doc.nuclear_family_id == user.nuclear_family_id
    if doc.visibility_tier == "PRIVATE_STRICT":
        released = doc.capsule_status == "RELEASED"
        is_recipient = doc.target_unlock_recipient_id == user.user_id
        return (is_recipient and released) or str(user.user_id) in _trustee_ids(doc)
    return False


def _read_denial(doc: Document, user: AuthenticatedUser, now: datetime) -> Optional[str]:
    """None when the caller may read the document, otherwise the reason."""
    if user.is_service or doc.uploader_id == user.user_id:
        return None
    if _is_sealed(doc, now):
        unlock_at = _as_utc(doc.time_capsule_unlock_at)
        return (
            f"Document is milestone-locked until {unlock_at.isoformat()}"
            if unlock_at
            else "Document is sealed until its trustees sign"
        )
    if not _tier_allows(doc, user):
        if doc.visibility_tier == "NUCLEAR_HOUSEHOLD":
            return "Access denied: Document is confidential to another nuclear household"
        return "Access denied: Private strict document restricted to uploader, trustees and designated recipient"
    return None


def _sealed_preview(doc: Document) -> DocumentResponse:
    """What a designated trustee sees of a sealed will: enough to review and sign, never the file."""
    return DocumentResponse.model_validate(doc).model_copy(
        update={"r2_storage_key": "", "extracted_metadata": {}}
    )


async def _load_clan_document(
    db: AsyncSession, doc_id: UUID, user: AuthenticatedUser, for_update: bool = False
) -> Document:
    """Fetch a document in the caller's clan. Foreign clans get a 404, not a 403,
    so document ids cannot be probed across tenants."""
    stmt = select(Document).where(Document.id == doc_id)
    if for_update:
        # Serialises concurrent trustee signatures on the same will.
        stmt = stmt.with_for_update()
    doc = (await db.execute(stmt)).scalars().first()
    if not doc or (not user.is_service and doc.joint_family_id != user.joint_family_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )
    return doc


async def _validate_trustees(
    db: AsyncSession, trustee_ids: List[UUID], joint_family_id: UUID, uploader_id: UUID
) -> List[str]:
    unique = list(dict.fromkeys(trustee_ids))
    if uploader_id in unique:
        raise HTTPException(status_code=400, detail="The document owner cannot be their own trustee")
    res = await db.execute(
        select(FamilyMembership.user_id).where(
            FamilyMembership.joint_family_id == joint_family_id,
            FamilyMembership.user_id.in_(unique),
            FamilyMembership.role.in_(("ADMIN", "MEMBER")),
        )
    )
    eligible = {row for row in res.scalars().all()}
    missing = [str(t) for t in unique if t not in eligible]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Trustees must be adult (ADMIN/MEMBER) members of this clan: {', '.join(missing)}",
        )
    return [str(t) for t in unique]


def _can_manage(doc: Document, user: AuthenticatedUser) -> bool:
    return doc.uploader_id == user.user_id or user.role == "ADMIN" or user.is_service


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@router.get("/", response_model=APIResponse[List[DocumentResponse]])
async def list_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    visibility: Optional[str] = Query(None, description="Filter by visibility tier"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[DocumentResponse]]:
    """List documents accessible to the current user subject to 3-tier RLS.
    Designated trustees also see sealed wills they must sign, with contents withheld."""
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    stmt = select(Document).where(Document.joint_family_id == current_user.joint_family_id)
    if category:
        stmt = stmt.where(Document.category == category)
    if visibility:
        stmt = stmt.where(Document.visibility_tier == visibility)

    docs = (await db.execute(stmt)).scalars().all()

    now_utc = datetime.now(timezone.utc)
    visible: List[DocumentResponse] = []
    for d in docs:
        if _read_denial(d, current_user, now_utc) is None:
            visible.append(DocumentResponse.model_validate(d))
        elif _is_sealed(d, now_utc) and str(current_user.user_id) in _trustee_ids(d):
            visible.append(_sealed_preview(d))

    return APIResponse(
        success=True,
        message=f"Retrieved {len(visible)} vault documents",
        data=visible,
    )


@router.post("/", response_model=APIResponse[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Upload metadata for a new document or milestone-locked time capsule."""
    require_writer(current_user, "upload documents to the vault")
    joint_family_id = require_clan(current_user)

    trustees: List[str] = []
    if doc_in.designated_trustee_ids:
        trustees = await _validate_trustees(
            db, doc_in.designated_trustee_ids, joint_family_id, current_user.user_id
        )
        if doc_in.trustee_approvals_required > len(trustees):
            raise HTTPException(status_code=400, detail="Quorum cannot exceed the number of trustees")

    # A future unlock date or a trustee quorum only protects anything if the
    # capsule actually starts sealed.
    capsule_status = doc_in.capsule_status
    unlock_at = _as_utc(doc_in.time_capsule_unlock_at)
    if capsule_status == "ACTIVE" and (
        (unlock_at and unlock_at > datetime.now(timezone.utc)) or doc_in.trustee_approvals_required > 0
    ):
        capsule_status = "LOCKED"

    new_doc = Document(
        joint_family_id=joint_family_id,
        nuclear_family_id=current_user.nuclear_family_id,
        uploader_id=current_user.user_id,
        title=doc_in.title,
        description=doc_in.description,
        category=doc_in.category,
        visibility_tier=doc_in.visibility_tier,
        r2_storage_key=doc_in.r2_storage_key,
        file_size_bytes=doc_in.file_size_bytes,
        mime_type=doc_in.mime_type,
        checksum_sha256=doc_in.checksum_sha256,
        capsule_status=capsule_status,
        time_capsule_unlock_at=doc_in.time_capsule_unlock_at,
        trustee_approvals_required=doc_in.trustee_approvals_required,
        trustee_approvals_received=[],
        designated_trustee_ids=trustees,
        target_unlock_recipient_id=doc_in.target_unlock_recipient_id,
        extracted_metadata={},
    )

    db.add(new_doc)
    await db.flush()
    await db.refresh(new_doc)

    return APIResponse(
        success=True,
        message=f"Document '{new_doc.title}' registered successfully in vault",
        data=DocumentResponse.model_validate(new_doc),
    )


@router.get("/milestones/badges", response_model=APIResponse[List[dict]])
async def get_milestone_badges(
    recipient_id: Optional[UUID] = Query(None, description="Filter milestones by target recipient"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[dict]]:
    """
    Sprint 5 Milestone Badging Endpoint:
    Provides badge metadata matching MilestoneNodeBadge.tsx on frontend lineage canvas.
    Badges are metadata only (no storage keys), scoped to the caller's clan.
    """
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    stmt = select(Document).where(
        Document.joint_family_id == current_user.joint_family_id,
        Document.capsule_status.isnot(None),
    )
    if recipient_id:
        stmt = stmt.where(Document.target_unlock_recipient_id == recipient_id)

    docs = (await db.execute(stmt)).scalars().all()

    badges = []
    for d in docs:
        is_will = d.category in ("LEGACY_WILL", "WILL") or bool(d.trustee_approvals_required)
        is_released = d.capsule_status == "RELEASED"
        badges.append({
            "id": str(d.id),
            "title": d.title,
            "type": "digital_will" if is_will else "time_capsule",
            "status": "UNLOCKED" if is_released else "SEALED",
            "unlockDate": d.time_capsule_unlock_at.isoformat() if d.time_capsule_unlock_at else None,
            "requiredSignatures": d.trustee_approvals_required or (2 if is_will else 0),
            "currentSignatures": len(d.trustee_approvals_received or []),
            "targetRecipientId": str(d.target_unlock_recipient_id) if d.target_unlock_recipient_id else None,
        })

    return APIResponse(
        success=True,
        message=f"Retrieved {len(badges)} milestone badges",
        data=badges,
    )


@router.get("/{doc_id}", response_model=APIResponse[DocumentResponse])
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Retrieve document details, enforcing Three-Tier RLS and milestone locks."""
    doc = await _load_clan_document(db, doc_id, current_user)

    denial = _read_denial(doc, current_user, datetime.now(timezone.utc))
    if denial:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denial)

    return APIResponse(
        success=True,
        message=f"Document '{doc.title}' retrieved successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.put("/{doc_id}", response_model=APIResponse[DocumentResponse])
async def update_document(
    doc_id: UUID,
    doc_in: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Update document metadata. Allowed only for uploader or clan ADMIN."""
    doc = await _load_clan_document(db, doc_id, current_user)

    if not _can_manage(doc, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the document uploader or clan administrator can edit metadata",
        )

    update_data = doc_in.model_dump(exclude_unset=True)
    target_household = update_data.get("nuclear_family_id")
    if target_household is not None:
        household = (
            await db.execute(select(NuclearFamily).where(NuclearFamily.id == target_household))
        ).scalars().first()
        if not household or household.joint_family_id != doc.joint_family_id:
            raise HTTPException(status_code=400, detail="Target household is not part of this clan")

    for field, value in update_data.items():
        setattr(doc, field, value)

    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"Document '{doc.title}' updated successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.put("/{doc_id}/trustees", response_model=APIResponse[DocumentResponse])
async def designate_trustees(
    doc_id: UUID,
    body: TrusteeDesignationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Name the trustees whose signatures release a digital will (uploader only).
    Resets collected signatures so a changed trustee set starts a fresh quorum."""
    doc = await _load_clan_document(db, doc_id, current_user, for_update=True)
    if doc.uploader_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the document owner can designate trustees")
    if doc.capsule_status == "RELEASED":
        raise HTTPException(status_code=409, detail="Document is already released")

    trustees = await _validate_trustees(db, body.trustee_ids, doc.joint_family_id, doc.uploader_id)
    required = body.approvals_required or doc.trustee_approvals_required or len(trustees)
    if required > len(trustees):
        raise HTTPException(status_code=400, detail="Quorum cannot exceed the number of trustees")

    doc.designated_trustee_ids = trustees
    doc.trustee_approvals_required = required
    doc.trustee_approvals_received = []
    if doc.capsule_status == "ACTIVE":
        doc.capsule_status = "LOCKED"

    record_audit(db, current_user, doc.joint_family_id, "TRUSTEES_DESIGNATED", "documents", doc.id, request)
    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"{len(trustees)} trustees designated, {required} signatures required",
        data=DocumentResponse.model_validate(doc),
    )


@router.patch("/{doc_id}/unlock", response_model=APIResponse[DocumentResponse])
async def unlock_time_capsule(
    doc_id: UUID,
    request: Request,
    unlock_in: Optional[TimeCapsuleUnlockRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """
    Milestone Time Capsule release.
    Transitions LOCKED/TRUSTEE_PENDING to RELEASED when the unlock date has passed,
    the trustee quorum is met, or the owner chooses to open their own capsule early.
    Trustee signatures are recorded through POST /{doc_id}/sign, not here.
    """
    doc = await _load_clan_document(db, doc_id, current_user, for_update=True)

    if doc.capsule_status == "RELEASED":
        return APIResponse(
            success=True,
            message="Time capsule is already released and accessible",
            data=DocumentResponse.model_validate(doc),
        )

    now_utc = datetime.now(timezone.utc)
    unlock_at = _as_utc(doc.time_capsule_unlock_at)
    date_reached = unlock_at is not None and now_utc >= unlock_at
    quorum_met = doc.trustee_approvals_required > 0 and (
        len(doc.trustee_approvals_received or []) >= doc.trustee_approvals_required
    )
    owner_release = doc.uploader_id == current_user.user_id

    if not (date_reached or quorum_met or owner_release):
        detail = (
            f"Capsule stays sealed until {unlock_at.isoformat()}"
            if unlock_at
            else "Capsule stays sealed until its trustees sign"
        )
        if doc.trustee_approvals_required:
            detail += f" ({len(doc.trustee_approvals_received or [])}/{doc.trustee_approvals_required} signatures)"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    doc.capsule_status = "RELEASED"
    record_audit(db, current_user, doc.joint_family_id, "CAPSULE_RELEASED", "documents", doc.id, request)
    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"Time capsule '{doc.title}' released successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.post("/{doc_id}/sign", response_model=APIResponse[DocumentResponse])
async def sign_milestone_document(
    doc_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """
    Sprint 5 Multi-Trustee Governance:
    Record a trustee approval on a digital will or locked capsule. Only designated
    trustees may sign (documents without a designation accept any adult clan member).
    Signatures are idempotent; when the quorum is met the document is RELEASED.
    """
    doc = await _load_clan_document(db, doc_id, current_user, for_update=True)

    if doc.capsule_status == "RELEASED":
        return APIResponse(
            success=True,
            message="Document is already released",
            data=DocumentResponse.model_validate(doc),
        )
    if not doc.trustee_approvals_required:
        raise HTTPException(status_code=400, detail="This document does not require trustee signatures")

    signer = str(current_user.user_id)
    trustees = _trustee_ids(doc)
    if trustees and signer not in trustees:
        raise HTTPException(status_code=403, detail="Only designated trustees can sign this document")
    if not trustees:
        require_writer(current_user, "sign milestone documents")

    approvals = list(doc.trustee_approvals_received or [])
    if signer not in approvals:
        approvals.append(signer)
        doc.trustee_approvals_received = approvals
        record_audit(db, current_user, doc.joint_family_id, "TRUSTEE_SIGNED", "documents", doc.id, request)

    if len(approvals) >= doc.trustee_approvals_required:
        doc.capsule_status = "RELEASED"
        record_audit(db, current_user, doc.joint_family_id, "CAPSULE_RELEASED", "documents", doc.id, request)
    else:
        doc.capsule_status = "TRUSTEE_PENDING"

    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"Trustee signature recorded. Quorum: {len(approvals)}/{doc.trustee_approvals_required}",
        data=DocumentResponse.model_validate(doc),
    )


@router.delete("/{doc_id}", response_model=APIResponse[dict])
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Delete a document record from vault."""
    doc = await _load_clan_document(db, doc_id, current_user)

    if not _can_manage(doc, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the document uploader or clan administrator can delete documents",
        )

    await db.delete(doc)
    await db.flush()

    return APIResponse(
        success=True,
        message=f"Document '{doc.title}' removed from vault",
        data={"deleted_id": str(doc_id)},
    )
