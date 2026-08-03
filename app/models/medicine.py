from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

from app.models.medicine_schedule import MedicineSchedule
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.refill_request import RefillRequest

class Medicine(Base):

    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    strength: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
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
    
    medicine_schedules: Mapped[list["MedicineSchedule"]] = relationship(
        back_populates="medicine",
    )
    
    refill_requests: Mapped[list["RefillRequest"]] = relationship(
        back_populates="medicine",
    )