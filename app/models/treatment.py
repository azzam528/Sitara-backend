from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Date,
    DateTime,
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


class TreatmentPhase(str, Enum):
    INTENSIVE = "intensive"
    CONTINUATION = "continuation"


class TreatmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"


class RegimenEnum(str, Enum):
    CATEGORY_1 = "category_1"
    CATEGORY_2 = "category_2"
    MDR = "mdr"


class Treatment(Base):

    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True)

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="treatments"
    )

    diagnosis_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    therapy_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    therapy_end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    phase: Mapped[TreatmentPhase] = mapped_column(
        SQLEnum(TreatmentPhase),
        nullable=False,
    )

    regimen: Mapped[RegimenEnum] = mapped_column(
        SQLEnum(RegimenEnum),
        nullable=False,
    )

    status: Mapped[TreatmentStatus] = mapped_column(
        SQLEnum(TreatmentStatus),
        default=TreatmentStatus.ACTIVE,
        nullable=False,
    )

    doctor_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    doctor_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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