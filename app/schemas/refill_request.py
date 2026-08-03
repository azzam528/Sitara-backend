from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class RefillRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefillCreate(BaseModel):

    treatment_id: int

    medicine_id: int

    quantity: int

    reason: str

    description: str | None = None


class RefillUpdate(BaseModel):

    status: RefillRequestStatus | None = None

    nurse_note: str | None = None


class RefillResponse(BaseModel):

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
        from_attributes=True,
    )