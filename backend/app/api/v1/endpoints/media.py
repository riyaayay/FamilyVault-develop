from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.models.media import MediaContribution
from app.schemas.media import (
    MediaContributionCreate,
    MediaContributionResponse,
    MediaTriageRequest,
    BatchTriageRequest,
    BatchTriageResponse,
)
from app.schemas.common import APIResponse

router = APIRouter()


def normalize_triage_status(raw_status: str) -> str:
    s = raw_status.strip().upper()
    if s in ("AUTO_PUBLISHED", "ACCEPTED", "APPROVED"):
        return "AUTO_PUBLISHED"
    elif s in ("REJECTED", "DECLINED"):
        return "REJECTED"
    elif s in ("PENDING_INBOX", "PENDING"):
        return "PENDING_INBOX"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid triage status '{raw_status}'. Allowed: 'AUTO_PUBLISHED', 'REJECTED'",
    )


@router.get("/inbox", response_model=APIResponse[List[MediaContributionResponse]])
async def get_media_inbox(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[MediaContributionResponse]]:
    """
    Query media contributions pending manual review and triage by clan/household admin.
    Sprint 4 D2 deliverable matching frontend media inbox.
    """
    stmt = select(MediaContribution).where(MediaContribution.status == "PENDING_INBOX")
    res = await db.execute(stmt)
    items = res.scalars().all()

    response_data = [MediaContributionResponse.model_validate(item) for item in items]
    return APIResponse(
        success=True,
        message=f"Retrieved {len(response_data)} pending items in media inbox",
        data=response_data,
    )


@router.get("/timeline/{user_id}", response_model=APIResponse[List[MediaContributionResponse]])
async def get_user_media_timeline(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[MediaContributionResponse]]:
    """
    Retrieve published media tagged with the given member UUID for their generational timeline.
    Sprint 4 timeline integration.
    """
    user_id_str = str(user_id)
    stmt = select(MediaContribution).where(MediaContribution.status == "AUTO_PUBLISHED")
    res = await db.execute(stmt)
    all_published = res.scalars().all()

    # Filter where face matched user or user uploaded
    matched = []
    for item in all_published:
        faces = item.matched_face_ids or []
        if user_id_str in faces or str(item.uploader_id) == user_id_str:
            matched.append(MediaContributionResponse.model_validate(item))

    return APIResponse(
        success=True,
        message=f"Retrieved {len(matched)} published media items for member timeline",
        data=matched,
    )


@router.post("/", response_model=APIResponse[MediaContributionResponse], status_code=status.HTTP_201_CREATED)
async def register_media_contribution(
    media_in: MediaContributionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[MediaContributionResponse]:
    """Register newly uploaded media and biometric matching results into the vault."""
    if current_user.role == "VIEWER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer accounts are not permitted to contribute media assets",
        )

    joint_family_id = media_in.joint_family_id or current_user.joint_family_id or UUID("11111111-1111-1111-1111-111111111111")
    uploader_id = media_in.uploader_id or current_user.user_id

    # Auto-publish if all matched faces have high confidence (>= 0.85)
    initial_status = "PENDING_INBOX"
    if media_in.confidence_scores:
        scores = list(media_in.confidence_scores.values())
        if scores and all(s >= 0.85 for s in scores) and len(scores) == 1:
            initial_status = "AUTO_PUBLISHED"

    new_media = MediaContribution(
        joint_family_id=joint_family_id,
        uploader_id=uploader_id,
        media_title=media_in.media_title,
        media_type=media_in.media_type,
        r2_storage_key=media_in.r2_storage_key,
        matched_face_ids=media_in.matched_face_ids,
        confidence_scores=media_in.confidence_scores,
        status=initial_status,
        approval_timestamp=datetime.now(timezone.utc) if initial_status == "AUTO_PUBLISHED" else None,
    )

    db.add(new_media)
    await db.flush()
    await db.refresh(new_media)

    return APIResponse(
        success=True,
        message="Media contribution registered successfully",
        data=MediaContributionResponse.model_validate(new_media),
    )


@router.patch("/{media_id}/triage", response_model=APIResponse[MediaContributionResponse])
async def triage_media(
    media_id: UUID,
    triage_in: MediaTriageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[MediaContributionResponse]:
    """
    Accept or reject an individual media item from the inbox.
    Sets status to AUTO_PUBLISHED or REJECTED and records audit details.
    """
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to triage media assets",
        )

    stmt = select(MediaContribution).where(MediaContribution.id == media_id)
    res = await db.execute(stmt)
    item = res.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media contribution '{media_id}' not found",
        )

    target_status = normalize_triage_status(triage_in.status)
    item.status = target_status
    item.approved_by = current_user.user_id
    item.approval_timestamp = datetime.now(timezone.utc)
    if triage_in.rejection_reason:
        item.rejection_reason = triage_in.rejection_reason

    await db.flush()
    await db.refresh(item)

    return APIResponse(
        success=True,
        message=f"Media item '{media_id}' successfully triaged as {target_status}",
        data=MediaContributionResponse.model_validate(item),
    )


@router.post("/batch-triage", response_model=APIResponse[BatchTriageResponse])
async def batch_triage_media(
    batch_in: BatchTriageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[BatchTriageResponse]:
    """
    Bulk triage endpoint for household heads to accept or reject multiple media items at once.
    Sprint 4 D2 requirement requested by Raghuvendra.
    """
    if current_user.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to perform batch triage on media assets",
        )

    target_status = normalize_triage_status(batch_in.status)
    succeeded: List[UUID] = []
    failed: List[UUID] = []

    stmt = select(MediaContribution).where(MediaContribution.id.in_(batch_in.media_ids))
    res = await db.execute(stmt)
    items = {item.id: item for item in res.scalars().all()}

    now_utc = datetime.now(timezone.utc)
    for m_id in batch_in.media_ids:
        item = items.get(m_id)
        if item:
            item.status = target_status
            item.approved_by = current_user.user_id
            item.approval_timestamp = now_utc
            if batch_in.rejection_reason:
                item.rejection_reason = batch_in.rejection_reason
            succeeded.append(m_id)
        else:
            failed.append(m_id)

    await db.flush()

    return APIResponse(
        success=True,
        message=f"Batch triage completed: {len(succeeded)} updated to {target_status}, {len(failed)} not found",
        data=BatchTriageResponse(
            processed_count=len(succeeded),
            succeeded_ids=succeeded,
            failed_ids=failed,
            status=target_status,
        ),
    )


@router.get("/{media_id}", response_model=APIResponse[MediaContributionResponse])
async def get_media_item(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[MediaContributionResponse]:
    """Retrieve details of a single media contribution."""
    stmt = select(MediaContribution).where(MediaContribution.id == media_id)
    res = await db.execute(stmt)
    item = res.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media contribution '{media_id}' not found",
        )

    return APIResponse(
        success=True,
        message="Media item retrieved successfully",
        data=MediaContributionResponse.model_validate(item),
    )
