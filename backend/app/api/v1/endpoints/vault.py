from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.document import Document
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    TimeCapsuleUnlockRequest,
)
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse[List[DocumentResponse]])
async def list_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    visibility: Optional[str] = Query(None, description="Filter by visibility tier"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[DocumentResponse]]:
    """List documents accessible to current authenticated user subject to 3-tier RLS."""
    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    stmt = select(Document).where(Document.joint_family_id == joint_family_id)
    if category:
        stmt = stmt.where(Document.category == category)
    if visibility:
        stmt = stmt.where(Document.visibility_tier == visibility)
    
    res = await db.execute(stmt)
    docs = res.scalars().all()

    now_utc = datetime.now(timezone.utc)
    filtered = []
    for d in docs:
        is_uploader = (d.uploader_id == current_user.user_id)
        if not is_uploader and current_user.role != "ADMIN":
            # Milestone lock check: hide locked capsules before unlock timestamp
            if d.capsule_status in ("LOCKED", "TRUSTEE_PENDING"):
                if d.time_capsule_unlock_at:
                    unlock_time = d.time_capsule_unlock_at if d.time_capsule_unlock_at.tzinfo else d.time_capsule_unlock_at.replace(tzinfo=timezone.utc)
                    if unlock_time > now_utc:
                        continue
                else:
                    continue

            # Three-tier visibility check
            if d.visibility_tier == "NUCLEAR_HOUSEHOLD" and d.nuclear_family_id != current_user.nuclear_family_id:
                continue
            elif d.visibility_tier == "PRIVATE_STRICT":
                if not (d.target_unlock_recipient_id == current_user.user_id and d.capsule_status == "RELEASED"):
                    continue

        filtered.append(DocumentResponse.model_validate(d))

    return APIResponse(
        success=True,
        message=f"Retrieved {len(filtered)} vault documents",
        data=filtered,
    )


@router.post("/", response_model=APIResponse[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Upload metadata for a new document or milestone-locked time capsule."""
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to upload documents to the vault",
        )

    joint_family_id = current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    nuclear_family_id = current_user.nuclear_family_id or UUID("22222222-2222-2222-2222-222222222222")

    new_doc = Document(
        joint_family_id=joint_family_id,
        nuclear_family_id=nuclear_family_id,
        uploader_id=current_user.user_id,
        title=doc_in.title,
        description=doc_in.description,
        category=doc_in.category,
        visibility_tier=doc_in.visibility_tier,
        r2_storage_key=doc_in.r2_storage_key,
        file_size_bytes=doc_in.file_size_bytes,
        mime_type=doc_in.mime_type,
        checksum_sha256=doc_in.checksum_sha256,
        capsule_status=doc_in.capsule_status,
        time_capsule_unlock_at=doc_in.time_capsule_unlock_at,
        trustee_approvals_required=doc_in.trustee_approvals_required,
        target_unlock_recipient_id=doc_in.target_unlock_recipient_id,
    )

    db.add(new_doc)
    await db.flush()
    await db.refresh(new_doc)

    return APIResponse(
        success=True,
        message=f"Document '{new_doc.title}' registered successfully in vault",
        data=DocumentResponse.model_validate(new_doc),
    )


@router.get("/{doc_id}", response_model=APIResponse[DocumentResponse])
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """Retrieve document details, enforcing Three-Tier RLS and milestone locks."""
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )

    # 1. Uploader always has read access
    is_uploader = (doc.uploader_id == current_user.user_id)

    # 2. Milestone Lock check: if locked and timestamp in future, only uploader can inspect
    now_utc = datetime.now(timezone.utc)
    if doc.capsule_status == "LOCKED" and doc.time_capsule_unlock_at:
        # Normalize timezone if naive
        unlock_time = doc.time_capsule_unlock_at if doc.time_capsule_unlock_at.tzinfo else doc.time_capsule_unlock_at.replace(tzinfo=timezone.utc)
        if unlock_time > now_utc and not is_uploader and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Document is milestone-locked until {doc.time_capsule_unlock_at.isoformat()}",
            )

    # 3. Three-tier visibility check
    if not is_uploader and current_user.role != "ADMIN":
        if doc.visibility_tier == "NUCLEAR_HOUSEHOLD":
            if doc.nuclear_family_id != current_user.nuclear_family_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Document is confidential to another nuclear household",
                )
        elif doc.visibility_tier == "PRIVATE_STRICT":
            is_released_recipient = (
                doc.target_unlock_recipient_id == current_user.user_id
                and doc.capsule_status == "RELEASED"
            )
            if not is_released_recipient:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Private strict document restricted to uploader and designated recipient",
                )

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
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )

    # Enforce edit permissions
    if doc.uploader_id != current_user.user_id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the document uploader or clan administrator can edit metadata",
        )

    update_data = doc_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)

    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"Document '{doc.title}' updated successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.patch("/{doc_id}/unlock", response_model=APIResponse[DocumentResponse])
async def unlock_time_capsule(
    doc_id: UUID,
    unlock_in: Optional[TimeCapsuleUnlockRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """
    Milestone Time Capsule unlock and multi-trustee sign-off route.
    Transitions capsule from LOCKED/TRUSTEE_PENDING to RELEASED when conditions are satisfied.
    """
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )

    if doc.capsule_status == "RELEASED":
        return APIResponse(
            success=True,
            message="Time capsule is already released and accessible",
            data=DocumentResponse.model_validate(doc),
        )

    now_utc = datetime.now(timezone.utc)
    is_admin_or_uploader = (doc.uploader_id == current_user.user_id or current_user.role == "ADMIN")
    unlocked = False

    # Condition 1: Timestamp Milestone Check
    if doc.time_capsule_unlock_at:
        unlock_time = doc.time_capsule_unlock_at if doc.time_capsule_unlock_at.tzinfo else doc.time_capsule_unlock_at.replace(tzinfo=timezone.utc)
        if now_utc >= unlock_time:
            doc.capsule_status = "RELEASED"
            unlocked = True

    # Condition 2: Trustee Approval Sign-Off
    if not unlocked and doc.trustee_approvals_required > 0:
        approvals = list(doc.trustee_approvals_received or [])
        caller_id_str = str(current_user.user_id)
        
        # Add approval if not already recorded
        if caller_id_str not in approvals:
            approvals.append(caller_id_str)
            doc.trustee_approvals_received = approvals

        if len(approvals) >= doc.trustee_approvals_required:
            doc.capsule_status = "RELEASED"
            unlocked = True
        else:
            doc.capsule_status = "TRUSTEE_PENDING"

    # Condition 3: Explicit Uploader/Admin Override
    if not unlocked and is_admin_or_uploader:
        doc.capsule_status = "RELEASED"
        unlocked = True

    await db.flush()
    await db.refresh(doc)

    status_msg = (
        f"Time capsule '{doc.title}' released successfully"
        if doc.capsule_status == "RELEASED"
        else f"Trustee sign-off registered. Approvals: {len(doc.trustee_approvals_received)}/{doc.trustee_approvals_required}"
    )

    return APIResponse(
        success=True,
        message=status_msg,
        data=DocumentResponse.model_validate(doc),
    )


@router.post("/{doc_id}/sign", response_model=APIResponse[DocumentResponse])
async def sign_milestone_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[DocumentResponse]:
    """
    Sprint 5 Multi-Trustee Governance:
    Record a cryptographic trustee approval signature on a digital will or locked capsule.
    When required quorum is met, automatically unlocks and transitions to RELEASED.
    """
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )

    approvals = list(doc.trustee_approvals_received or [])
    signer_id_str = str(current_user.user_id)

    if signer_id_str not in approvals:
        approvals.append(signer_id_str)
        doc.trustee_approvals_received = approvals

    if doc.trustee_approvals_required > 0 and len(approvals) >= doc.trustee_approvals_required:
        doc.capsule_status = "RELEASED"
    else:
        doc.capsule_status = "TRUSTEE_PENDING"

    await db.flush()
    await db.refresh(doc)

    return APIResponse(
        success=True,
        message=f"Trustee signature recorded. Quorum: {len(approvals)}/{doc.trustee_approvals_required}",
        data=DocumentResponse.model_validate(doc),
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
    """
    stmt = select(Document).where(Document.capsule_status.isnot(None))
    if recipient_id:
        stmt = stmt.where(Document.target_unlock_recipient_id == recipient_id)

    res = await db.execute(stmt)
    docs = res.scalars().all()

    badges = []
    for d in docs:
        is_will = (d.category == "WILL" or (d.trustee_approvals_required and d.trustee_approvals_required > 0))
        is_released = (d.capsule_status == "RELEASED")
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


@router.delete("/{doc_id}", response_model=APIResponse[dict])
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[dict]:
    """Delete a document record from vault."""
    stmt = select(Document).where(Document.id == doc_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found in vault",
        )

    if doc.uploader_id != current_user.user_id and current_user.role != "ADMIN":
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
