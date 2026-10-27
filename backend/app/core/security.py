import hmac
from functools import lru_cache
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings, PLACEHOLDER_SERVICE_KEY
from app.core.database import get_db

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
service_key_header = APIKeyHeader(name="X-Service-Key", auto_error=False)

# Seeded Vance clan, used by the service role and the local developer fallback.
DEFAULT_CLAN_ID = UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_HOUSEHOLD_ID = UUID("22222222-2222-2222-2222-222222222222")

# When a person belongs to several households, act with their strongest role.
ROLE_PRIORITY = {"ADMIN": 0, "MEMBER": 1, "CHILD": 2, "VIEWER": 3}
WRITE_ROLES = ("ADMIN", "MEMBER")


class AuthenticatedUser(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    role: str = "MEMBER"
    joint_family_id: Optional[UUID] = None
    nuclear_family_id: Optional[UUID] = None

    @property
    def is_service(self) -> bool:
        return self.role == "SERVICE_ROLE"

    @property
    def can_write(self) -> bool:
        return self.role in WRITE_ROLES or self.is_service


def _service_user(full_name: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
        email="service-sync@familyvault.app",
        full_name=full_name,
        role="SERVICE_ROLE",
        joint_family_id=DEFAULT_CLAN_ID,
        nuclear_family_id=DEFAULT_HOUSEHOLD_ID,
    )


def _is_valid_service_key(key: str) -> bool:
    candidates = {settings.SUPABASE_SERVICE_ROLE_KEY, settings.SERVICE_API_KEY}
    if not settings.dev_auth_enabled:
        candidates.discard(PLACEHOLDER_SERVICE_KEY)
    else:
        candidates.add(PLACEHOLDER_SERVICE_KEY)
    return any(hmac.compare_digest(key, candidate) for candidate in candidates if candidate)


@lru_cache(maxsize=1)
def _jwks_client() -> "jwt.PyJWKClient":
    url = settings.SUPABASE_JWKS_URL or f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(url, cache_keys=True)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify a Supabase access token (legacy HS256 secret or JWKS-published key)."""
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        key: Any = settings.SUPABASE_JWT_SECRET
    elif alg in ("ES256", "RS256"):
        key = _jwks_client().get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidAlgorithmError(f"Unsupported token algorithm: {alg}")
    return jwt.decode(token, key, algorithms=[alg], options={"verify_aud": False})


async def _resolve_membership(db: AsyncSession, user_id: UUID):
    """Tenant and clan role are authoritative in family_memberships, never in token claims."""
    from app.models.family import FamilyMembership

    res = await db.execute(select(FamilyMembership).where(FamilyMembership.user_id == user_id))
    memberships = res.scalars().all()
    if not memberships:
        return None
    return min(memberships, key=lambda m: ROLE_PRIORITY.get(m.role, len(ROLE_PRIORITY)))


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    service_key: Optional[str] = Depends(service_key_header),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """
    Validates Supabase JWTs or service-role keys and returns the caller's tenant context.
    The clan, household and role are looked up from family_memberships, so a forged
    or stale role claim can never widen access. Falls back to a developer context only
    when DEBUG is on outside production.
    """
    # 1. Service key (sync scripts such as graph-service), via header or raw bearer
    provided_key = api_key or service_key
    if not provided_key and credentials and _is_valid_service_key(credentials.credentials):
        provided_key = credentials.credentials

    if provided_key:
        if _is_valid_service_key(provided_key):
            return _service_user("Graph Sync Service Role")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 2. Supabase access token
    if credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            if payload.get("role") == "service_role":
                return _service_user("Supabase Service Role")

            user_id_str = payload.get("sub") or payload.get("user_id")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token payload missing subject identifier",
                )
            user_id = UUID(user_id_str)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        membership = await _resolve_membership(db, user_id)
        return AuthenticatedUser(
            user_id=user_id,
            email=payload.get("email", ""),
            full_name=(payload.get("user_metadata") or {}).get("full_name", "Family Member"),
            # Signed-in but not yet invited into a clan: authenticated, no tenant, read nothing.
            role=membership.role if membership else "GUEST",
            joint_family_id=membership.joint_family_id if membership else None,
            nuclear_family_id=membership.nuclear_family_id if membership else None,
        )

    # 3. Local developer fallback (never in production)
    if settings.dev_auth_enabled:
        return AuthenticatedUser(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="runeet@familyvault.app",
            full_name="Runeet (Lead Admin)",
            role="ADMIN",
            joint_family_id=DEFAULT_CLAN_ID,
            nuclear_family_id=DEFAULT_HOUSEHOLD_ID,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_clan(current_user: AuthenticatedUser) -> UUID:
    """The caller's joint family, or 403 for authenticated users without one."""
    if not current_user.joint_family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not a member of any family clan yet",
        )
    return current_user.joint_family_id


def require_writer(current_user: AuthenticatedUser, action: str) -> None:
    if not current_user.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' is not authorized to {action}",
        )
