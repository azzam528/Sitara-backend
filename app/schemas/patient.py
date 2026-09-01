from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.patient import GenderEnum

# ==========================
# CREATE
# ==========================


class PatientCreate(BaseModel):

    medical_record_number: str = Field(max_length=20)

    full_name: str = Field(max_length=255)

    nik: str = Field(min_length=16, max_length=16)

    birth_date: date

    gender: GenderEnum

    phone: str = Field(max_length=15)

    address: str

    occupation: str = Field(max_length=100)

    pmo_name: str = Field(max_length=100)

    pmo_phone: str = Field(max_length=15)

    clinical_note: str | None = None


# ==========================
# UPDATE
# ==========================


class PatientUpdate(BaseModel):

    full_name: str | None = Field(default=None, max_length=255)

    phone: str | None = Field(default=None, max_length=15)

    address: str | None = None

    occupation: str | None = Field(default=None, max_length=100)

    pmo_name: str | None = Field(default=None, max_length=100)

    pmo_phone: str | None = Field(default=None, max_length=15)

    clinical_note: str | None = None


# ==========================
# RESPONSE
# ==========================


class PatientResponse(BaseModel):

    id: int

    user_id: int

    medical_record_number: str

    full_name: str

    nik: str

    birth_date: date

    gender: GenderEnum

    phone: str

    address: str

    occupation: str

    pmo_name: str

    pmo_phone: str

    clinical_note: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================
# CREATE RESPONSE
# ==========================


class PatientCreateResponse(BaseModel):

    patient: PatientResponse

    username: str

    activation_url: str

    whatsapp_url: str


class ActivationResendResponse(BaseModel):

    message: str

    whatsapp_url: str