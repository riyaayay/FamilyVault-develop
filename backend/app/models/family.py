import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class JointFamily(Base, TimestampMixin):
    __tablename__ = "joint_families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    ancestral_origin = Column(String(255), nullable=True)
    motto = Column(Text, nullable=True)

    # Relationships
    nuclear_families = relationship("NuclearFamily", back_populates="joint_family", cascade="all, delete-orphan")
    memberships = relationship("FamilyMembership", back_populates="joint_family", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="joint_family")
    properties = relationship("Property", back_populates="joint_family")


class NuclearFamily(Base, TimestampMixin):
    __tablename__ = "nuclear_families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    household_name = Column(String(255), nullable=False)
    current_city = Column(String(100), nullable=True)

    # Relationships
    joint_family = relationship("JointFamily", back_populates="nuclear_families")
    memberships = relationship("FamilyMembership", back_populates="nuclear_family")
    documents = relationship("Document", back_populates="nuclear_family")
    pets = relationship("Pet", back_populates="nuclear_family")


class FamilyMembership(Base):
    __tablename__ = "family_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joint_family_id = Column(UUID(as_uuid=True), ForeignKey("joint_families.id", ondelete="CASCADE"), nullable=False, index=True)
    nuclear_family_id = Column(UUID(as_uuid=True), ForeignKey("nuclear_families.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(
        ENUM("ADMIN", "MEMBER", "CHILD", "VIEWER", name="user_role", create_type=False),
        default="MEMBER",
        nullable=False,
    )
    relation_to_head = Column(
        ENUM("HEAD", "SPOUSE", "CHILD", "PARENT", "SIBLING", "EXTENDED", name="family_relation", create_type=False),
        default="EXTENDED",
        nullable=False,
    )
    is_emergency_contact = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="memberships")
    joint_family = relationship("JointFamily", back_populates="memberships")
    nuclear_family = relationship("NuclearFamily", back_populates="memberships")
