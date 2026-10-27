from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MedicationItem(BaseModel):
    name: str
    dosage: str
    frequency: str
    instructions: Optional[str] = None


class HealthRecordBase(BaseModel):
    blood_group: Optional[str] = None
    allergies: List[str] = []
    chronic_conditions: List[str] = []
    current_medications: List[MedicationItem] = []
    emergency_notes: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    primary_physician_contact: Optional[str] = None
    is_emergency_visible: bool = True


class HealthRecordResponse(HealthRecordBase):
    id: UUID
    user_id: UUID
    nuclear_family_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmergencyContact(BaseModel):
    name: str
    relation: str
    phone_number: Optional[str] = None


class EmergencyDossierResponse(BaseModel):
    """
    Emergency Red Alert Medical Dossier.
    Instantly compiled for emergency responders or family members.
    """
    patient_id: UUID
    full_name: str
    date_of_birth: Optional[str] = None
    blood_group: Optional[str] = None
    critical_allergies: List[str]
    chronic_conditions: List[str]
    active_medications: List[MedicationItem]
    emergency_contacts: List[EmergencyContact]
    insurance_policy_number: Optional[str] = None
    primary_physician_contact: Optional[str] = None
    emergency_notes: Optional[str] = None
    compiled_at: datetime
    tamper_proof_hash: str
