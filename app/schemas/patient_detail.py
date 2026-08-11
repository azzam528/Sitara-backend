from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from app.models.patient import GenderEnum
from app.models.treatment import (
    TreatmentPhase,
    TreatmentStatus,
    RegimenEnum,
)
from app.schemas.patient import PatientResponse
from app.schemas.control_schedule import ControlScheduleStatus
from app.schemas.refill_request import RefillRequestStatus


class PatientDetailTreatment(BaseModel):
    id: int
    patient_id: int

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

    model_config = ConfigDict(
        from_attributes=True
    )


class PatientDetailControlSchedule(BaseModel):
    id: int
    treatment_id: int

    control_date: date
    control_time: time

    status: ControlScheduleStatus
    doctor_note: str | None

    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class PatientDetailRefill(BaseModel):
    id: int

    treatment_id: int
    medicine_id: int

    quantity: int

    reason: str
    description: str | None

    status: RefillRequestStatus

    nurse_note: str | None

    approved_by: int | None
    approved_at: datetime | None

    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class PatientDetailResponse(BaseModel):
    patient: PatientResponse

    treatment: PatientDetailTreatment | None

    next_control: PatientDetailControlSchedule | None

    refills: list[PatientDetailRefill]