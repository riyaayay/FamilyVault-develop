from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: e.g. initialize connections, verify configurations
    print(f"[{settings.PROJECT_NAME}] Starting up in {settings.ENVIRONMENT} mode...")
    yield
    # Shutdown: e.g. close connection pools
    print(f"[{settings.PROJECT_NAME}] Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    description="""
    ## FamilyVault Core Enterprise Backend API
    **Lead Architect:** Runeet
    
    Features:
    * **Three-Tier Row Level Security (RLS)**: `JOINT_CLAN`, `NUCLEAR_HOUSEHOLD`, `PRIVATE_STRICT`.
    * **Milestone-Locked Vault & Digital Will**: Unlock on date or trustee approval.
    * **Emergency Red Alert Protocol**: One-click medical dossier compilation (`POST /api/v1/health/emergency-dossier/{user_id}`).
    * **Single Source of Truth UUID Sync**: Synchronized across PostgreSQL, Neo4j, and InsightFace.
    """,
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/healthz", tags=["System"])
async def root_health_check():
    """Liveness probe for cloud infrastructure (Railway / Render)."""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": "0.1.0"}
