from datetime import datetime, date
from enum import Enum

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

    verification_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    video_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
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