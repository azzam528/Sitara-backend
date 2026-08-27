from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Enum as SQLEnum,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.face_verification import FaceVerification


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class VideoVerification(Base):

    __tablename__ = "video_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    medicine_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_schedules.id"),
        nullable=False,
    )

    face_verification_id: Mapped[int | None] = mapped_column(
        ForeignKey("face_verifications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    verification_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    video_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        nullable=False,
    )

    thumbnail_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ai_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
    )

    review_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    medicine_schedule = relationship(
        "MedicineSchedule",
        back_populates="video_verifications",
    )

    face_verification: Mapped["FaceVerification | None"] = relationship(
        "FaceVerification",
        back_populates="video_verifications",
    )

    @property
    def patient(self):
        if self.medicine_schedule and self.medicine_schedule.treatment:
            return self.medicine_schedule.treatment.patient
        return None

    @property
    def treatment(self):
        if self.medicine_schedule:
            return self.medicine_schedule.treatment
        return None
