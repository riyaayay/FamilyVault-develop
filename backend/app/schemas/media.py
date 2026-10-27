from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MediaContributionBase(BaseModel):
    media_title: Optional[str] = None
    media_type: str = "image/jpeg"
    r2_storage_key: str
    matched_face_ids: List[str] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class MediaContributionCreate(MediaContributionBase):
    joint_family_id: Optional[UUID] = None
    uploader_id: Optional[UUID] = None


class MediaTriageRequest(BaseModel):
    status: str = Field(..., description="'AUTO_PUBLISHED' | 'REJECTED' or 'accepted' | 'rejected'")
    rejection_reason: Optional[str] = None


class BatchTriageRequest(BaseModel):
    media_ids: List[UUID]
    status: str = Field(..., description="'AUTO_PUBLISHED' | 'REJECTED' or 'accepted' | 'rejected'")
    rejection_reason: Optional[str] = None


class MediaContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    joint_family_id: UUID
    uploader_id: UUID
    media_title: Optional[str] = None
    media_type: str
    r2_storage_key: str
    matched_face_ids: List[Any] = Field(default_factory=list)
    confidence_scores: Dict[str, Any] = Field(default_factory=dict)
    status: str
    approved_by: Optional[UUID] = None
    approval_timestamp: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BatchTriageResponse(BaseModel):
    processed_count: int
    succeeded_ids: List[UUID]
    failed_ids: List[UUID] = Field(default_factory=list)
    status: str
