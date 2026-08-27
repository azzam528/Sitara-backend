from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class PatientVideoResponse(BaseModel):
    id: int
    full_name: str
    nik: str
    medical_record_number: str
    phone: str | None = None
    address: str | None = None
    pmo_name: str | None = None
    pmo_phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TreatmentVideoResponse(BaseModel):
    id: int
    phase: str | None = None
    regimen: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VideoVerificationCreate(BaseModel):
    medicine_schedule_id: int
    face_verification_id: int | None = None
    verification_date: date
    video_path: str
    file_name: str
    mime_type: str
    file_size: int
    thumbnail_path: str | None = None


class VideoVerificationUpdate(BaseModel):
    ai_confidence: float | None = None
    status: VerificationStatus | None = None
    review_note: str | None = None


class VideoVerificationResponse(BaseModel):
    id: int
    medicine_schedule_id: int
    face_verification_id: int | None = None
    verification_date: date
    video_path: str
    file_name: str
    mime_type: str
    file_size: int
    thumbnail_path: str | None = None
    ai_confidence: float | None = None
    status: VerificationStatus
    review_note: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    patient: PatientVideoResponse | None = None
    treatment: TreatmentVideoResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )
