from datetime import datetime, date, time
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Time,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.treatment import Treatment


class ControlScheduleStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class ControlSchedule(Base):

    __tablename__ = "control_schedules"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    treatment_id: Mapped[int] = mapped_column(
        ForeignKey("treatments.id"),
        nullable=False,
    )

    control_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    control_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    status: Mapped[ControlScheduleStatus] = mapped_column(
        SQLEnum(ControlScheduleStatus),
        default=ControlScheduleStatus.PENDING,
        nullable=False,
    )

    doctor_note: Mapped[str | None] = mapped_column(
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

    treatment: Mapped["Treatment"] = relationship(
        back_populates="control_schedules",
    )