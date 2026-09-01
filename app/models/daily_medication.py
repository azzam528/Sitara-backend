from datetime import date, datetime, time
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.medicine_schedule import MedicineSchedule


class DailyMedicationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    MISSED = "missed"
    REJECTED = "rejected"


class VotStep(str, Enum):
    WAITING = "waiting"
    FACE_VERIFIED = "face_verified"
    MEDICINE_DETECTED = "medicine_detected"
    MEDICINE_MATCHED = "medicine_matched"
    DRINKING = "drinking"
    VERIFIED = "verified"


class DailyMedication(Base):

    __tablename__ = "daily_medications"

    id: Mapped[int] = mapped_column(primary_key=True)

    medicine_schedule_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_schedules.id"),
        nullable=False,
        index=True,
    )

    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    scheduled_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    status: Mapped[DailyMedicationStatus] = mapped_column(
        SQLEnum(
            DailyMedicationStatus,
            values_callable=lambda enums: [item.value for item in enums],
        ),
        default=DailyMedicationStatus.PENDING,
        nullable=False,
    )

    vot_step: Mapped[VotStep] = mapped_column(
        SQLEnum(
            VotStep,
            values_callable=lambda enums: [item.value for item in enums],
        ),
        default=VotStep.WAITING,
        nullable=False,
    )

    face_verification_id: Mapped[int | None] = mapped_column(
        ForeignKey("face_verifications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    video_verification_id: Mapped[int | None] = mapped_column(
        ForeignKey("video_verifications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    max_drinking_stage: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    medicine_schedule: Mapped["MedicineSchedule"] = relationship(
        back_populates="daily_medications",
    )

    __table_args__ = (
        UniqueConstraint(
            "medicine_schedule_id",
            "scheduled_date",
            name="uq_daily_medications_schedule_date",
        ),
    )
