from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class MedicineScheduleCreate(BaseModel):

    treatment_id: int

    medicine_id: int

    dosage: str = Field(max_length=100)

    quantity_initial: int

    quantity_remaining: int

    drink_time: time


class MedicineScheduleUpdate(BaseModel):

    dosage: str

    quantity_initial: int

    quantity_remaining: int

    drink_time: time


class MedicineScheduleResponse(BaseModel):

    id: int

    treatment_id: int

    medicine_id: int

    dosage: str

    quantity_initial: int

    quantity_remaining: int

    drink_time: time

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyMedicineScheduleResponse(BaseModel):
    treatment_id: int
    medicine_id: int
    medicine_name: str

    dosage: str
    quantity_initial: int
    quantity_remaining: int
    drink_time: time

    model_config = ConfigDict(
        from_attributes=True,
    )
