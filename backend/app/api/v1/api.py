from fastapi import APIRouter
from app.api.v1.endpoints import health, vault, users, pets, properties, media

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health & Emergency Dossier"])
api_router.include_router(vault.router, prefix="/vault", tags=["Document Vault & Time Capsule"])
api_router.include_router(media.router, prefix="/media", tags=["Media Ingestion, Triage & Timeline"])
api_router.include_router(users.router, prefix="/users", tags=["Users & Clan Directory"])
api_router.include_router(users.household_router, prefix="/household", tags=["Household Roster"])
api_router.include_router(pets.router, prefix="/pets", tags=["Pets & Household Assets"])
api_router.include_router(properties.router, prefix="/properties", tags=["Properties & Real Estate Assets"])

