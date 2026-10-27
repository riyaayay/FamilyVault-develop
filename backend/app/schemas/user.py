from typing import Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str
    preferred_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HouseholdMemberResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    name: str
    role: str
    relation_to_head: Optional[str] = None
    initials: str
    accent: str = "chart-1"
    species: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    clan_id: Optional[UUID] = None
    clan_name: Optional[str] = None
    joint_family_id: Optional[UUID] = None
    generation: Optional[int] = None
    is_pet: bool = False

    model_config = ConfigDict(from_attributes=True)


class ClanPersonSyncResponse(BaseModel):
    """
    1:1 Schema mapping to graph-service PersonIn and contracts/graph-tree-response.json.
    Enables graph-service to pull person data directly into Neo4j AuraDB.
    """
    person_id: UUID
    full_name: str
    role: str = "MEMBER"
    relation_to_head: str = "EXTENDED"
    generation: int = 1
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    is_living: bool = True
    avatar_url: Optional[str] = None
    nuclear_household: Optional[str] = None
    clan_id: UUID
    clan_name: str

    model_config = ConfigDict(from_attributes=True)


