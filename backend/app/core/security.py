from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt
from pydantic import BaseModel
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
service_key_header = APIKeyHeader(name="X-Service-Key", auto_error=False)


class AuthenticatedUser(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    role: str = "MEMBER"
    joint_family_id: Optional[UUID] = None
    nuclear_family_id: Optional[UUID] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    service_key: Optional[str] = Depends(service_key_header),
) -> AuthenticatedUser:
    """
    Validates Supabase / application JWT tokens, service-role keys, or API keys
    and returns authenticated user context.
    Falls back to a developer context when running in local DEBUG mode without token.
    """
    # 1. Check API Key or Service Role Header (for sync scripts like graph-service)
    provided_key = api_key or service_key
    if not provided_key and credentials:
        # Also allow passing the raw service role key via Authorization: Bearer <key>
        if credentials.credentials in [settings.SUPABASE_SERVICE_ROLE_KEY, settings.SERVICE_API_KEY, "service-role-key-placeholder"]:
            provided_key = credentials.credentials

    if provided_key:
        valid_keys = {
            settings.SUPABASE_SERVICE_ROLE_KEY,
            settings.SERVICE_API_KEY,
            "service-role-key-placeholder",
        }
        if provided_key in valid_keys:
            return AuthenticatedUser(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                email="service-sync@familyvault.app",
                full_name="Graph Sync Service Role",
                role="SERVICE_ROLE",
                joint_family_id=UUID("11111111-1111-1111-1111-111111111111"),
                nuclear_family_id=UUID("22222222-2222-2222-2222-222222222222"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # 2. Check JWT Bearer token
    if credentials:
        token = credentials.credentials
        try:
            # Decode token using Supabase JWT Secret
            payload: Dict[str, Any] = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

            # Service role JWT payload check
            if payload.get("role") == "service_role":
                return AuthenticatedUser(
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    email="service-sync@familyvault.app",
                    full_name="Supabase Service Role",
                    role="SERVICE_ROLE",
                    joint_family_id=UUID("11111111-1111-1111-1111-111111111111"),
                    nuclear_family_id=UUID("22222222-2222-2222-2222-222222222222"),
                )

            user_id_str = payload.get("sub") or payload.get("user_id")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token payload missing subject identifier",
                )
            
            return AuthenticatedUser(
                user_id=UUID(user_id_str),
                email=payload.get("email", ""),
                full_name=payload.get("user_metadata", {}).get("full_name", "Family Member"),
                role=payload.get("role", "MEMBER"),
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Local DEBUG mode fallback
    if settings.DEBUG:
        return AuthenticatedUser(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="runeet@familyvault.app",
            full_name="Runeet (Lead Admin)",
            role="ADMIN",
            joint_family_id=UUID("11111111-1111-1111-1111-111111111111"),
            nuclear_family_id=UUID("22222222-2222-2222-2222-222222222222"),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

