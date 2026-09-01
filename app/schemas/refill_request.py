from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class RefillRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PickupFacilityResponse(BaseModel):
    id: int
    name: str
    address: str | None
    phone: str | None
    latitude: float | None
    longitude: float | None

    model_config = ConfigDict(from_attributes=True)


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

    pickup_facility: PickupFacilityResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class RefillPatientResponse(BaseModel):
    id: int
    full_name: str
    nik: str | None = None
    medical_record_number: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RefillMedicineResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class RefillTreatmentResponse(BaseModel):
    id: int
    patient: RefillPatientResponse

    model_config = ConfigDict(from_attributes=True)


class RefillListResponse(BaseModel):
    id: int
    treatment_id: int
    medicine_id: int

    treatment: RefillTreatmentResponse
    medicine: RefillMedicineResponse

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

    pickup_facility: PickupFacilityResponse | None = None

    model_config = ConfigDict(from_attributes=True)
