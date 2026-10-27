from typing import Optional
from uuid import UUID
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser
from app.models.household import AuditLog


def record_audit(
    db: AsyncSession,
    current_user: AuthenticatedUser,
    joint_family_id: Optional[UUID],
    event_type: str,
    target_resource: str,
    target_resource_id: Optional[UUID] = None,
    request: Optional[Request] = None,
) -> None:
    """Append an immutable security-trail row in the caller's transaction.

    Sensitive reads (emergency dossiers) and state transitions (capsule
    release, trustee signatures, media triage) are logged so clan admins
    can answer "who saw or changed this, and when".
    """
    if joint_family_id is None:
        return
    db.add(
        AuditLog(
            # The service role has no users row; keep the FK valid.
            actor_id=None if current_user.is_service else current_user.user_id,
            joint_family_id=joint_family_id,
            event_type=event_type,
            target_resource=target_resource,
            target_resource_id=target_resource_id,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
