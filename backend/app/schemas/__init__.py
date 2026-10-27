from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.user import UserBase, UserCreate, UserResponse
from app.schemas.document import (
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    TimeCapsuleUnlockRequest,
)
from app.schemas.health import (
    HealthRecordBase,
    HealthRecordResponse,
    EmergencyDossierResponse,
    EmergencyContact,
    MedicationItem,
)
from app.schemas.household import (
    PetBase,
    PetCreate,
    PetUpdate,
    PetResponse,
    PropertyBase,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
)

__all__ = [
    "APIResponse",
    "PaginatedResponse",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "TimeCapsuleUnlockRequest",
    "HealthRecordBase",
    "HealthRecordResponse",
    "EmergencyDossierResponse",
    "EmergencyContact",
    "MedicationItem",
    "PetBase",
    "PetCreate",
    "PetUpdate",
    "PetResponse",
    "PropertyBase",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyResponse",
]
