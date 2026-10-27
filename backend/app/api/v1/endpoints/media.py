from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.audit import record_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser, require_clan, require_writer
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


def _is_tagged(item: MediaContribution, user_id: UUID) -> bool:
    return str(user_id) in (item.matched_face_ids or [])


def _may_view(item: MediaContribution, user: AuthenticatedUser) -> bool:
    """Mirrors the media RLS policy; household reviewers also see the pending queue."""
    if user.is_service or item.status == "AUTO_PUBLISHED":
        return True
    if item.uploader_id == user.user_id or _is_tagged(item, user.user_id):
        return True
    return item.status == "PENDING_INBOX" and user.can_write


async def _load_clan_media(db: AsyncSession, media_id: UUID, user: AuthenticatedUser) -> MediaContribution:
    item = (await db.execute(select(MediaContribution).where(MediaContribution.id == media_id))).scalars().first()
    if not item or (not user.is_service and item.joint_family_id != user.joint_family_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media contribution '{media_id}' not found",
        )
    return item


@router.get("/inbox", response_model=APIResponse[List[MediaContributionResponse]])
async def get_media_inbox(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[MediaContributionResponse]]:
    """
    Query media contributions pending manual review and triage by clan/household admin.
    Sprint 4 D2 deliverable matching frontend media inbox.
    """
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    stmt = select(MediaContribution).where(
        MediaContribution.status == "PENDING_INBOX",
        MediaContribution.joint_family_id == current_user.joint_family_id,
    ).order_by(MediaContribution.created_at.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()

    response_data = [
        MediaContributionResponse.model_validate(item) for item in items if _may_view(item, current_user)
    ]
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
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    user_id_str = str(user_id)
    stmt = select(MediaContribution).where(
        MediaContribution.status == "AUTO_PUBLISHED",
        MediaContribution.joint_family_id == current_user.joint_family_id,
    )
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


@router.get("/timeline", response_model=APIResponse[List[MediaContributionResponse]])
async def get_clan_lore_timeline(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[MediaContributionResponse]]:
    """Generational Lore timeline: every published photo, audio and video memory in the clan, newest first."""
    if not current_user.joint_family_id:
        return APIResponse(success=True, message="No clan membership", data=[])

    stmt = (
        select(MediaContribution)
        .where(
            MediaContribution.status == "AUTO_PUBLISHED",
            MediaContribution.joint_family_id == current_user.joint_family_id,
        )
        .order_by(MediaContribution.created_at.desc())
        .limit(limit)
    )
    items = (await db.execute(stmt)).scalars().all()
    data = [MediaContributionResponse.model_validate(i) for i in items]
    return APIResponse(success=True, message=f"Retrieved {len(data)} lore memories", data=data)


@router.get("/archive", response_model=APIResponse[List[MediaContributionResponse]])
async def get_my_media_archive(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[List[MediaContributionResponse]]:
    """The caller's own uploads in every state. Rejected media is never deleted;
    it stays here, in the sender's private archive."""
    stmt = (
        select(MediaContribution)
        .where(MediaContribution.uploader_id == current_user.user_id)
        .order_by(MediaContribution.created_at.desc())
    )
    items = (await db.execute(stmt)).scalars().all()
    data = [MediaContributionResponse.model_validate(i) for i in items]
    return APIResponse(success=True, message=f"Retrieved {len(data)} archived uploads", data=data)


@router.post("/", response_model=APIResponse[MediaContributionResponse], status_code=status.HTTP_201_CREATED)
async def register_media_contribution(
    media_in: MediaContributionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[MediaContributionResponse]:
    """Register newly uploaded media and biometric matching results into the vault."""
    if current_user.role in ("VIEWER", "GUEST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer accounts are not permitted to contribute media assets",
        )

    # Tenant and uploader come from the session; only the sync service may
    # register media on someone else's behalf.
    joint_family_id = require_clan(current_user)
    uploader_id = current_user.user_id
    if current_user.is_service:
        joint_family_id = media_in.joint_family_id or joint_family_id
        uploader_id = media_in.uploader_id or uploader_id

    # Auto-publish a confident single-face image (same rule as the biometrics
    # service); video, audio, group photos and weak matches wait in the inbox.
    initial_status = "PENDING_INBOX"
    if media_in.confidence_scores and media_in.media_type.startswith("image"):
        scores = list(media_in.confidence_scores.values())
        if len(scores) == 1 and scores[0] >= settings.MATCH_THRESHOLD:
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> APIResponse[MediaContributionResponse]:
    """
    Accept or reject an individual media item from the inbox.
    Sets status to AUTO_PUBLISHED or REJECTED and records audit details.
    """
    require_writer(current_user, "triage media assets")
    item = await _load_clan_media(db, media_id, current_user)

    target_status = normalize_triage_status(triage_in.status)
    item.status = target_status
    item.approved_by = current_user.user_id
    item.approval_timestamp = datetime.now(timezone.utc)
    if triage_in.rejection_reason:
        item.rejection_reason = triage_in.rejection_reason
    record_audit(db, current_user, item.joint_family_id, f"MEDIA_{target_status}", "media_contributions", item.id, request)

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
    require_writer(current_user, "perform batch triage on media assets")
    joint_family_id = require_clan(current_user)

    target_status = normalize_triage_status(batch_in.status)
    succeeded: List[UUID] = []
    failed: List[UUID] = []

    stmt = select(MediaContribution).where(MediaContribution.id.in_(batch_in.media_ids))
    res = await db.execute(stmt)
    # Items from other clans are reported as not found.
    items = {
        item.id: item
        for item in res.scalars().all()
        if current_user.is_service or item.joint_family_id == joint_family_id
    }

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
    item = await _load_clan_media(db, media_id, current_user)
    if not _may_view(item, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This media is awaiting review and is not visible to you yet",
        )

    return APIResponse(
        success=True,
        message="Media item retrieved successfully",
        data=MediaContributionResponse.model_validate(item),
    )
