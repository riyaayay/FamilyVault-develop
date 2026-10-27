from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    SUPABASE_SERVICE_ROLE_KEY: str = "service-role-key-placeholder"
    SERVICE_API_KEY: str = "service-role-key-placeholder"
    SUPABASE_JWT_SECRET: str = "jwt-secret-placeholder"


    # Cloudflare R2
    R2_ACCOUNT_ID: str = "r2-account-placeholder"
    R2_ACCESS_KEY_ID: str = "r2-access-key-placeholder"
    R2_SECRET_ACCESS_KEY: str = "r2-secret-placeholder"
    R2_BUCKET_NAME: str = "familyvault-media"
    R2_PUBLIC_DOMAIN: str = "https://media.familyvault.app"

    # Shared Biometric Match Constant
    MATCH_THRESHOLD: float = 0.85

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
