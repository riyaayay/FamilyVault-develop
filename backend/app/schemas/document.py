from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str  # FINANCIAL, PROPERTY, HEALTH, IDENTITY, LEGACY_WILL, MEMORABILIA
    visibility_tier: str = "NUCLEAR_HOUSEHOLD"  # JOINT_CLAN, NUCLEAR_HOUSEHOLD, PRIVATE_STRICT


class DocumentCreate(DocumentBase):
    r2_storage_key: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: Optional[str] = None
    capsule_status: str = "ACTIVE"
    time_capsule_unlock_at: Optional[datetime] = None
    trustee_approvals_required: int = 0
    target_unlock_recipient_id: Optional[UUID] = None


class DocumentResponse(DocumentBase):
    id: UUID
    joint_family_id: UUID
    nuclear_family_id: Optional[UUID] = None
    uploader_id: UUID
    r2_storage_key: str
    file_size_bytes: int
    mime_type: str
    capsule_status: str
    time_capsule_unlock_at: Optional[datetime] = None
    trustee_approvals_required: int
    trustee_approvals_received: List[Any]
    extracted_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    visibility_tier: Optional[str] = None
    nuclear_family_id: Optional[UUID] = None


class TimeCapsuleUnlockRequest(BaseModel):
    trustee_notes: Optional[str] = None
