from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ComplaintStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class ComplaintCreate(BaseModel):

    treatment_id: int

    category: str

    description: str


class ComplaintUpdate(BaseModel):

    status: ComplaintStatus | None = None

    response: str | None = None

    handled_by: int | None = None


class ComplaintResponse(BaseModel):

    id: int

    treatment_id: int

    handled_by: int | None

    category: str

    description: str

    status: ComplaintStatus

    response: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )