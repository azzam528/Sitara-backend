from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.models.daily_medication import DailyMedicationStatus, VotStep
from app.schemas.medicine_detection import BoundingBox


class TodayMedicationResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    medicine_id: int
    medicine_name: str
    dosage: str
    scheduled_date: date
    scheduled_time: time
    quantity_remaining: int
    status: DailyMedicationStatus
    vot_step: VotStep
    eligible: bool

    model_config = ConfigDict(from_attributes=True)


class VotStartRequest(BaseModel):
    medicine_schedule_id: int


class VotSessionResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    medicine_id: int
    medicine_name: str
    dosage: str
    scheduled_date: date
    scheduled_time: time
    quantity_remaining: int
    status: DailyMedicationStatus
    vot_step: VotStep
    attempt_count: int = 0
    can_retry: bool = True
    failure_reason: str | None = None
    max_drinking_stage: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VotStartResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    status: DailyMedicationStatus
    vot_step: VotStep
    scheduled_date: date
    scheduled_time: time
    attempt_count: int = 0


class VotFaceVerifyResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    face_verification_id: int
    verified: bool
    similarity_score: float
    threshold: float
    status: str
    vot_step: VotStep
    message: str
    attempt_count: int = 0
    can_retry: bool = True
    failure_reason: str | None = None


class VotMedicineDetectResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    expected_medicine: str
    detected_medicine: str | None = None
    confidence: float = 0.0
    bounding_box: BoundingBox | None = None
    medicine_match: bool
    status: DailyMedicationStatus
    vot_step: VotStep
    message: str
    attempt_count: int = 0
    can_retry: bool = True
    failure_reason: str | None = None


class VotCompleteRequest(BaseModel):
    daily_medication_id: int
    drinking_verified: bool = True
    max_drinking_stage: str | None = None
    failure_reason: str | None = None


class VotCompleteResponse(BaseModel):
    daily_medication_id: int
    status: DailyMedicationStatus
    vot_step: VotStep
    completed_at: datetime | None = None
    message: str
    attempt_count: int = 0
    can_retry: bool = False
    failure_reason: str | None = None
    max_drinking_stage: str | None = None


class VotEscalateRequest(BaseModel):
    daily_medication_id: int
    failure_reason: str
    max_drinking_stage: str | None = None
    note: str | None = None
