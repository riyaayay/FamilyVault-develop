import json
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SERVICE_KEY = "service-role-key-placeholder"
PLACEHOLDER_JWT_SECRET = "jwt-secret-placeholder"


def _contract_match_threshold(default: float = 0.85) -> float:
    """MATCH_THRESHOLD lives once in contracts/MATCH_CONSTANTS.json.

    Looked up next to the app (docker image copies contracts/ in) and at the
    repo root (local runs), so the backend can never drift from biometrics.
    """
    backend_dir = Path(__file__).resolve().parents[2]
    for candidate in (backend_dir / "contracts", backend_dir.parent / "contracts"):
        path = candidate / "MATCH_CONSTANTS.json"
        if path.is_file():
            try:
                return float(json.loads(path.read_text(encoding="utf-8"))["MATCH_THRESHOLD"])
            except (OSError, ValueError, KeyError):
                break
    return default


class Settings(BaseSettings):
    PROJECT_NAME: str = "FamilyVault Core API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:1111",
        "http://127.0.0.1:1111",
        "http://localhost:5173",
        "https://familyvault.vercel.app",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []


    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

    # Supabase Credentials & Service Keys
    SUPABASE_URL: str = "https://example.supabase.co"
    SUPABASE_ANON_KEY: str = "anon-key-placeholder"
    SUPABASE_SERVICE_ROLE_KEY: str = PLACEHOLDER_SERVICE_KEY
    SERVICE_API_KEY: str = PLACEHOLDER_SERVICE_KEY
    SUPABASE_JWT_SECRET: str = PLACEHOLDER_JWT_SECRET
    # Newer Supabase projects sign access tokens asymmetrically (ES256/RS256).
    # Defaults to <SUPABASE_URL>/auth/v1/.well-known/jwks.json when unset.
    SUPABASE_JWKS_URL: Optional[str] = None

    # Signs the public 24-hour Emergency Red Alert pass (HMAC-SHA256).
    # Falls back to the JWT secret so local dev works with zero config.
    EMERGENCY_PASS_SECRET: Optional[str] = None
    EMERGENCY_PASS_TTL_HOURS: int = 24


    # Cloudflare R2
    R2_ACCOUNT_ID: str = "r2-account-placeholder"
    R2_ACCESS_KEY_ID: str = "r2-access-key-placeholder"
    R2_SECRET_ACCESS_KEY: str = "r2-secret-placeholder"
    R2_BUCKET_NAME: str = "familyvault-media"
    R2_PUBLIC_DOMAIN: str = "https://media.familyvault.app"

    # Shared Biometric Match Constant (single source: contracts/MATCH_CONSTANTS.json)
    MATCH_THRESHOLD: float = _contract_match_threshold()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @property
    def dev_auth_enabled(self) -> bool:
        """Unauthenticated developer fallback + placeholder keys. Never in production."""
        return self.DEBUG and not self.is_production

    @property
    def emergency_pass_secret(self) -> str:
        return self.EMERGENCY_PASS_SECRET or self.SUPABASE_JWT_SECRET

    def assert_production_ready(self) -> None:
        """Fail fast instead of booting a production API with demo credentials."""
        if not self.is_production:
            return
        problems = []
        if self.SUPABASE_JWT_SECRET == PLACEHOLDER_JWT_SECRET and "example.supabase.co" in self.SUPABASE_URL:
            problems.append("SUPABASE_JWT_SECRET (or a real SUPABASE_URL for JWKS) must be set")
        if PLACEHOLDER_SERVICE_KEY in (self.SUPABASE_SERVICE_ROLE_KEY, self.SERVICE_API_KEY):
            problems.append("SUPABASE_SERVICE_ROLE_KEY and SERVICE_API_KEY must not use placeholders")
        if self.DEBUG:
            problems.append("DEBUG must be False")
        if problems:
            raise RuntimeError("Refusing to start in production: " + "; ".join(problems))


settings = Settings()
