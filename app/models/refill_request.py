from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.treatment import Treatment
    from app.models.medicine import Medicine
    from app.models.user import User


class RefillRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefillRequest(Base):

    __tablename__ = "refill_requests"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    treatment_id: Mapped[int] = mapped_column(
        ForeignKey("treatments.id"),
        nullable=False,
    )

    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[RefillRequestStatus] = mapped_column(
        SQLEnum(RefillRequestStatus),
        default=RefillRequestStatus.PENDING,
        nullable=False,
    )

    nurse_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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
        back_populates="refill_requests",
    )

    medicine: Mapped["Medicine"] = relationship(
        back_populates="refill_requests",
    )

    approver: Mapped["User"] = relationship(
        foreign_keys=[approved_by],
    )
    
    