from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# PET SCHEMAS
# ==============================================================================

class PetBase(BaseModel):
    name: str = Field(..., description="Pet's given name")
    pet_type: str = Field("DOG", description="DOG, CAT, BIRD, or OTHER")
    breed: Optional[str] = Field(None, description="Breed description")
    date_of_birth: Optional[date] = Field(None, description="Pet date of birth")
    microchip_number: Optional[str] = Field(None, description="Unique microchip identifier")
    vaccination_schedule: List[Dict[str, Any]] = Field(default_factory=list, description="Array of { vaccine, administered_on, next_due }")


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: Optional[str] = None
    pet_type: Optional[str] = None
    breed: Optional[str] = None
    date_of_birth: Optional[date] = None
    microchip_number: Optional[str] = None
    vaccination_schedule: Optional[List[Dict[str, Any]]] = None


class PetResponse(PetBase):
    id: UUID
    nuclear_family_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PROPERTY SCHEMAS
# ==============================================================================

class PropertyBase(BaseModel):
    title: str = Field(..., description="Property or estate title")
    property_type: str = Field(..., description="e.g. Ancestral Land, Apartment, Agricultural Plot")
    survey_number: Optional[str] = Field(None, description="Government cadastre / survey registry number")
    address: str = Field(..., description="Full physical property address")
    estimated_valuation: Optional[Decimal] = Field(None, description="Estimated market valuation in INR")
    ownership_breakdown: List[Dict[str, Any]] = Field(default_factory=list, description="Array of { user_id, share_percentage }")
    deed_document_id: Optional[UUID] = Field(None, description="Foreign key to document vault deed record")


class PropertyCreate(PropertyBase):
    nuclear_family_id: Optional[UUID] = Field(None, description="Optional nuclear household assignment")


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    property_type: Optional[str] = None
    survey_number: Optional[str] = None
    address: Optional[str] = None
    estimated_valuation: Optional[Decimal] = None
    ownership_breakdown: Optional[List[Dict[str, Any]]] = None
    deed_document_id: Optional[UUID] = None
    nuclear_family_id: Optional[UUID] = None


class PropertyResponse(PropertyBase):
    id: UUID
    joint_family_id: UUID
    nuclear_family_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
