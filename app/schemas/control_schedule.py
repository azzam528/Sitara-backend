from datetime import (
    datetime,
    date,
    time,
)
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
)


class ControlScheduleStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class ControlScheduleCreate(BaseModel):

    treatment_id: int

    control_date: date

    control_time: time

    doctor_note: str | None = None


class ControlScheduleUpdate(BaseModel):

    control_date: date | None = None

    control_time: time | None = None

    status: ControlScheduleStatus | None = None

    doctor_note: str | None = None


class ControlScheduleResponse(BaseModel):

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
        from_attributes=True,
    )