import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class MediaContribution(Base, TimestampMixin):
    __tablename__ = "media_contributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    media_title = Column(String(255), nullable=True)
    media_type = Column(String(50), default="image/jpeg", nullable=False)
    r2_storage_key = Column(Text, nullable=False)

    # Biometric AI Results
    matched_face_ids = Column(JSONB, default=list, nullable=False)  # List of users.id UUID strings
    confidence_scores = Column(JSONB, default=dict, nullable=False)  # Map: { "<UUID>": 0.94 }

    # Inbox Workflow Status
    status = Column(
        ENUM("PENDING_INBOX", "AUTO_PUBLISHED", "REJECTED", name="media_status", create_type=False),
        default="PENDING_INBOX",
        nullable=False,
        index=True,
    )
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approval_timestamp = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="media_contributions", foreign_keys=[uploader_id])
