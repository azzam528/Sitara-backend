from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.treatment import (
    TreatmentPhase,
    TreatmentStatus,
    RegimenEnum,
)
from app.models.patient import GenderEnum


class TreatmentCreate(BaseModel):
    patient_id: int
    diagnosis_date: date
    therapy_start_date: date
    therapy_end_date: date
    phase: TreatmentPhase
    regimen: RegimenEnum
    doctor_name: str = Field(max_length=100)
    doctor_note: str | None = None


class TreatmentUpdate(BaseModel):
    diagnosis_date: date
    therapy_start_date: date
    therapy_end_date: date
    phase: TreatmentPhase
    regimen: RegimenEnum
    status: TreatmentStatus
    doctor_name: str
    doctor_note: str | None = None


# ==========================================
# PATIENT DATA UNTUK RESPONSE TREATMENT
# ==========================================


class PatientTreatmentResponse(BaseModel):
    id: int
    full_name: str
    nik: str
    medical_record_number: str
    birth_date: date | None = None
    gender: GenderEnum | None = None
    phone: str | None = None
    address: str | None = None
    occupation: str | None = None
    pmo_name: str | None = None
    pmo_phone: str | None = None
    clinical_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# RESPONSE NAKES
# ==========================================


class TreatmentResponse(BaseModel):
    id: int
    patient_id: int
    patient: PatientTreatmentResponse

    diagnosis_date: date
    therapy_start_date: date
    therapy_end_date: date
    phase: TreatmentPhase
    regimen: RegimenEnum
    status: TreatmentStatus
    doctor_name: str
    doctor_note: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# RESPONSE UNTUK PATIENT
# ==========================================


class MyTreatmentResponse(BaseModel):
    id: int
    patient_id: int
    therapy_start_date: date
    therapy_end_date: date
    phase: TreatmentPhase
    regimen: RegimenEnum
    status: TreatmentStatus
    doctor_name: str

    model_config = ConfigDict(
        from_attributes=True,
    )
