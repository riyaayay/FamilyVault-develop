import uuid
from sqlalchemy import Column, String, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    preferred_name = Column(String(100), nullable=True)
    avatar_url = Column(String, nullable=True)
    phone_number = Column(String(30), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    memberships = relationship("FamilyMembership", back_populates="user", cascade="all, delete-orphan")
    uploaded_documents = relationship("Document", back_populates="uploader", foreign_keys="Document.uploader_id")
    media_contributions = relationship("MediaContribution", back_populates="uploader", foreign_keys="MediaContribution.uploader_id")
    health_record = relationship("HealthRecord", back_populates="user", uselist=False)
