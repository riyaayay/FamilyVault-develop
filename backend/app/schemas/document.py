from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    trustee_approvals_required: int = Field(0, ge=0)
    target_unlock_recipient_id: Optional[UUID] = None
    designated_trustee_ids: List[UUID] = Field(default_factory=list)


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
    designated_trustee_ids: List[Any] = Field(default_factory=list)
    target_unlock_recipient_id: Optional[UUID] = None
    extracted_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("designated_trustee_ids", "trustee_approvals_received", mode="before")
    @classmethod
    def _none_as_empty_list(cls, v):
        return v or []

    @field_validator("extracted_metadata", mode="before")
    @classmethod
    def _none_as_empty_dict(cls, v):
        return v or {}


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    visibility_tier: Optional[str] = None
    nuclear_family_id: Optional[UUID] = None


class TimeCapsuleUnlockRequest(BaseModel):
    trustee_notes: Optional[str] = None


class TrusteeDesignationRequest(BaseModel):
    trustee_ids: List[UUID] = Field(..., min_length=1)
    approvals_required: Optional[int] = Field(None, ge=1)
