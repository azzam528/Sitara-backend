from datetime import date, time

from pydantic import BaseModel, ConfigDict

from app.models.daily_medication import DailyMedicationStatus, VotStep


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

    model_config = ConfigDict(from_attributes=True)


class VotStartResponse(BaseModel):
    daily_medication_id: int
    medicine_schedule_id: int
    status: DailyMedicationStatus
    vot_step: VotStep
    scheduled_date: date
    scheduled_time: time
