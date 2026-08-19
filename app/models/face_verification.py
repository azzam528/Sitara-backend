from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.medicine_schedule import MedicineSchedule
    from app.models.video_verification import VideoVerification


class FaceVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class FaceVerification(Base):
    __tablename__ = "face_verifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    medicine_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    status: Mapped[FaceVerificationStatus] = mapped_column(
        SQLEnum(FaceVerificationStatus),
        default=FaceVerificationStatus.PENDING,
        nullable=False,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="face_verifications",
    )

    medicine_schedule: Mapped["MedicineSchedule"] = relationship(
        back_populates="face_verifications",
    )

    video_verifications: Mapped[list["VideoVerification"]] = relationship(
        back_populates="face_verification",
    )
