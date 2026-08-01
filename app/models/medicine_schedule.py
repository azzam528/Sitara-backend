from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Time,
    DateTime,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base
from app.models.video_verification import VideoVerification

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.video_verification import VideoVerification

class MedicineSchedule(Base):

    __tablename__ = "medicine_schedules"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    treatment_id: Mapped[int] = mapped_column(
        ForeignKey("treatments.id"),
        nullable=False,
    )

    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"),
        nullable=False,
    )

    dosage: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    quantity_initial: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    quantity_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    drink_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
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
    
    treatment = relationship(
        "Treatment",
        back_populates="medicine_schedules",
    )

    medicine = relationship(
        "Medicine",
        back_populates="medicine_schedules",
    )
    
    video_verifications: Mapped[list["VideoVerification"]] = relationship(
        back_populates="medicine_schedule",
    )