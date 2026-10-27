import uuid
from sqlalchemy import Column, String, Text, Integer, BigInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    nuclear_family_id = Column(UUID(as_uuid=True), ForeignKey("nuclear_families.id", ondelete="SET NULL"), nullable=True, index=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        ENUM("FINANCIAL", "PROPERTY", "HEALTH", "IDENTITY", "LEGACY_WILL", "MEMORABILIA", "LEGAL", name="document_category", create_type=False),
        nullable=False,
        index=True,
    )
    visibility_tier = Column(
        ENUM("JOINT_CLAN", "NUCLEAR_HOUSEHOLD", "PRIVATE_STRICT", name="visibility_tier", create_type=False),
        default="NUCLEAR_HOUSEHOLD",
        nullable=False,
        index=True,
    )

    # Cloudflare R2 pointers
    r2_storage_key = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    checksum_sha256 = Column(String(64), nullable=True)

    # Milestone Lock & Time Capsule Properties
    capsule_status = Column(
        ENUM("ACTIVE", "LOCKED", "TRUSTEE_PENDING", "RELEASED", name="time_capsule_status", create_type=False),
        default="ACTIVE",
        nullable=False,
        index=True,
    )
    time_capsule_unlock_at = Column(DateTime(timezone=True), nullable=True)
    trustee_approvals_required = Column(Integer, default=0, nullable=False)
    trustee_approvals_received = Column(JSONB, default=list, nullable=False)
    target_unlock_recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Vision Ingestion Extracted Metadata
    extracted_metadata = Column(JSONB, default=dict, nullable=False)

    # Relationships
    joint_family = relationship("JointFamily", back_populates="documents")
    nuclear_family = relationship("NuclearFamily", back_populates="documents")
    uploader = relationship("User", back_populates="uploaded_documents", foreign_keys=[uploader_id])
