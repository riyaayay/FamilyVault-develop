import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class HealthRecord(Base, TimestampMixin):
    __tablename__ = "health_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    nuclear_family_id = Column(UUID(as_uuid=True), ForeignKey("nuclear_families.id", ondelete="CASCADE"), nullable=False)

    blood_group = Column(String(10), nullable=True)
    allergies = Column(ARRAY(String), default=list, nullable=True)
    chronic_conditions = Column(ARRAY(String), default=list, nullable=True)
    current_medications = Column(JSONB, default=list, nullable=False)  # Array of { name, dosage, frequency }
    emergency_notes = Column(Text, nullable=True)
    insurance_policy_number = Column(String(100), nullable=True)
    primary_physician_contact = Column(String(255), nullable=True)

    # Red Alert Emergency Flag
    is_emergency_visible = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="health_record")
