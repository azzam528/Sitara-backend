from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict



class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VideoVerificationCreate(BaseModel):

    medicine_schedule_id: int

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

    verification_date: date

    video_path: str

    file_name: str

    mime_type: str

    file_size: int

    thumbnail_path: str | None

    ai_confidence: float | None

    status: VerificationStatus

    review_note: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )