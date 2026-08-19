from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.notification import Notification
    from app.models.health_facility import HealthFacility
    from app.models.activation_token import ActivationToken


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Email tidak wajib untuk akun pasien
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(30), nullable=False)

    # =====================================================
    # HEALTH FACILITY
    # =====================================================

    # Sementara nullable=True karena database sudah
    # memiliki user lama.
    # Setelah migration + data existing selesai,
    # akan kita ubah menjadi nullable=False.

    facility_id: Mapped[int | None] = mapped_column(
        ForeignKey("health_facilities.id"),
        nullable=True,
    )

    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    patient: Mapped["Patient"] = relationship(back_populates="user", uselist=False)

    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")

    facility: Mapped["HealthFacility"] = relationship(
        "HealthFacility",
        back_populates="users",
    )
    
    activation_tokens: Mapped[list["ActivationToken"]] = relationship(
        "ActivationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
