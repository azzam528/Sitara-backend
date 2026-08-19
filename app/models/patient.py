from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Date,
    Text,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.treatment import Treatment
    from app.models.face_embedding import FaceEmbedding
    from app.models.face_verification import FaceVerification


class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"


class Patient(Base):

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="patient"
    )

    medical_record_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    nik: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
    )

    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    gender: Mapped[GenderEnum] = mapped_column(
        SQLEnum(GenderEnum),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    occupation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    pmo_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    pmo_phone: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    clinical_note: Mapped[str | None] = mapped_column(
        Text,
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

    treatments: Mapped[list["Treatment"]] = relationship(
        back_populates="patient"
    )

    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    face_verifications: Mapped[list["FaceVerification"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )