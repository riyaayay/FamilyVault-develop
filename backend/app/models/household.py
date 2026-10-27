import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Pet(Base, TimestampMixin):
    __tablename__ = "pets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nuclear_family_id = Column(UUID(as_uuid=True), ForeignKey("nuclear_families.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    pet_type = Column(
        ENUM("DOG", "CAT", "BIRD", "OTHER", name="pet_type", create_type=False),
        default="DOG",
        nullable=False,
    )
    breed = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    microchip_number = Column(String(100), nullable=True)
    vaccination_schedule = Column(JSONB, default=list, nullable=False)

    # Relationships
    nuclear_family = relationship("NuclearFamily", back_populates="pets")


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    nuclear_family_id = Column(UUID(as_uuid=True), ForeignKey("nuclear_families.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    property_type = Column(String(100), nullable=False)
    survey_number = Column(String(100), nullable=True)
    address = Column(Text, nullable=False)
    estimated_valuation = Column(Numeric(15, 2), nullable=True)
    ownership_breakdown = Column(JSONB, default=list, nullable=False)
    deed_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    joint_family = relationship("JointFamily", back_populates="properties")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    target_resource = Column(String(100), nullable=False)
    target_resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    event_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
