import secrets
import string
from datetime import date, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.patient import Patient
from app.models.activation_token import ActivationToken

from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.activation_token_repository import (
    ActivationTokenRepository,
)

from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
)

from app.core.config import settings

from app.core.security import (
    hash_password,
    generate_activation_token,
    hash_activation_token,
)


class PatientService:

    def __init__(self):

        self.user_repository = UserRepository()

        self.patient_repository = PatientRepository()

        self.activation_token_repository = ActivationTokenRepository()

    # =====================================================
    # GET ALL
    # =====================================================

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):
        return self.patient_repository.get_all_by_facility(
            db,
            current_user.facility_id,
        )

    # =====================================================
    # GENERATE PASSWORD
    # =====================================================

    def _generate_password(self, length: int = 10):

        characters = string.ascii_letters + string.digits

        return "".join(secrets.choice(characters) for _ in range(length))

    # =====================================================
    # GENERATE USERNAME
    # =====================================================

    def _normalize_phone(self, phone: str) -> str:

        phone = phone.strip().replace(" ", "").replace("-", "")

        if phone.startswith("+62"):
            phone = "62" + phone[3:]

        elif phone.startswith("0"):
            phone = "62" + phone[1:]

        elif not phone.startswith("62"):
            phone = "62" + phone

        return phone

    def _build_activation_url(self, raw_token: str) -> str:

        base_url = settings.ACTIVATION_BASE_URL.rstrip("/")

        return f"{base_url}/activate?token={raw_token}"

    def _build_activation_whatsapp_url(
        self,
        full_name: str,
        username: str,
        phone: str,
        activation_url: str,
    ) -> str:

        message = (
            f"Halo {full_name},\n\n"
            f"Akun SITARA Anda telah dibuat.\n\n"
            f"Username: {username}\n\n"
            f"Silakan aktivasi akun dan buat password "
            f"Anda melalui link berikut:\n\n"
            f"{activation_url}\n\n"
            f"Link aktivasi berlaku selama 24 jam.\n\n"
            f"Terima kasih."
        )

        return f"https://wa.me/{phone}?text={quote(message)}"

    # =====================================================
    # CREATE PATIENT
    # =====================================================

    def create_patient(
        self,
        db: Session,
        patient_data: PatientCreate,
        current_user: User,
    ):

        # -------------------------------------------------
        # Normalize WhatsApp & PMO Phone
        # -------------------------------------------------

        phone = self._normalize_phone(patient_data.phone)
        pmo_phone = (
            self._normalize_phone(patient_data.pmo_phone)
            if patient_data.pmo_phone
            else patient_data.pmo_phone
        )
        username = phone

        # -------------------------------------------------
        # Check active username / WhatsApp
        # -------------------------------------------------

        existing_user = self.user_repository.get_by_username(
            db,
            phone,
        )

        if existing_user is not None:

            if existing_user.role != "patient":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Nomor WhatsApp sudah terdaftar " "sebagai akun non-pasien."
                    ),
                )

            raise HTTPException(
                status_code=400,
                detail="Nomor WhatsApp sudah terdaftar sebagai akun.",
            )

        # -------------------------------------------------
        # Check active NIK
        # -------------------------------------------------

        existing_nik = self.patient_repository.get_by_nik(
            db,
            patient_data.nik,
        )

        if existing_nik:
            raise HTTPException(
                status_code=400,
                detail="NIK sudah terdaftar dalam sistem.",
            )

        # -------------------------------------------------
        # Check active Medical Record
        # -------------------------------------------------

        existing_mrn = self.patient_repository.get_by_medical_record_number(
            db,
            patient_data.medical_record_number,
        )

        if existing_mrn:
            raise HTTPException(
                status_code=400,
                detail="Nomor rekam medis sudah terdaftar.",
            )

        # -------------------------------------------------
        # Generate temporary password
        # -------------------------------------------------
        # Password ini hanya sebagai password internal.
        # Tidak dikirim ke pasien.
        # Pasien akan membuat password sendiri
        # melalui activation link.

        temporary_password = self._generate_password()

        try:
            # -------------------------------------------------
            # 1. Create User (Atomic - flush only)
            # -------------------------------------------------

            user = User(
                username=username,
                email=None,
                password_hash=hash_password(temporary_password),
                role="patient",
                facility_id=current_user.facility_id,
                must_change_password=True,
                is_active=True,
            )

            user = self.user_repository.create(
                db,
                user,
                commit=False,
            )

            # -------------------------------------------------
            # 2. Create Patient (Atomic - flush only)
            # -------------------------------------------------

            patient = Patient(
                user_id=user.id,
                medical_record_number=patient_data.medical_record_number,
                full_name=patient_data.full_name,
                nik=patient_data.nik,
                birth_date=patient_data.birth_date,
                gender=patient_data.gender,
                phone=phone,
                address=patient_data.address,
                occupation=patient_data.occupation,
                pmo_name=patient_data.pmo_name,
                pmo_phone=pmo_phone,
                clinical_note=patient_data.clinical_note,
            )

            patient = self.patient_repository.create(
                db,
                patient,
                commit=False,
            )

            # -------------------------------------------------
            # 3. Generate Activation Token (Atomic - flush only)
            # -------------------------------------------------

            raw_token = generate_activation_token()

            token_hash = hash_activation_token(raw_token)

            activation_token = ActivationToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=(datetime.utcnow() + timedelta(hours=24)),
            )

            self.activation_token_repository.create(
                db,
                activation_token,
                commit=False,
            )

            # -------------------------------------------------
            # 4. Generate Activation URL
            # -------------------------------------------------

            activation_url = self._build_activation_url(raw_token)

<<<<<<< HEAD
        whatsapp_url = self._build_activation_whatsapp_url(
            patient.full_name,
            username,
            phone,
            activation_url,
        )

        # -------------------------------------------------
        # Return
        # -------------------------------------------------
=======
            # -------------------------------------------------
            # 5. WhatsApp Message
            # -------------------------------------------------

            message = (
                f"Halo {patient.full_name},\n\n"
                f"Akun SITARA Anda telah dibuat.\n\n"
                f"Username: {username}\n\n"
                f"Silakan aktivasi akun dan buat password "
                f"Anda melalui link berikut:\n\n"
                f"{activation_url}\n\n"
                f"Link aktivasi berlaku selama 24 jam.\n\n"
                f"Terima kasih."
            )

            whatsapp_url = f"https://wa.me/{phone}" f"?text={quote(message)}"

            # -------------------------------------------------
            # 6. Single Commit for the Entire Transaction
            # -------------------------------------------------
>>>>>>> origin/haikal

            db.commit()
            db.refresh(patient)

            # -------------------------------------------------
            # Return
            # -------------------------------------------------

            return {
                "patient": patient,
                "username": username,
                "activation_url": activation_url,
                "whatsapp_url": whatsapp_url,
            }
        except Exception:
            db.rollback()
            raise

    # =====================================================
    # GET BY ID
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        patient_id: int,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_id_and_facility(
            db,
            patient_id,
            current_user.facility_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return patient

    # =====================================================
    # UPDATE
    # =====================================================

    def update_patient(
        self,
        db: Session,
        patient_id: int,
        patient_data: PatientUpdate,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_id_and_facility(
            db,
            patient_id,
            current_user.facility_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        update_data = patient_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(patient, key, value)

        return self.patient_repository.update(
            db,
            patient,
        )

    # =====================================================
    # DELETE
    # =====================================================

    def delete_patient(
        self,
        db: Session,
        patient_id: int,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_id_and_facility(
            db,
            patient_id,
            current_user.facility_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        return self.patient_repository.delete(
            db,
            patient,
        )

    # =====================================================
    # RESEND ACTIVATION
    # =====================================================

    def resend_activation(
        self,
        db: Session,
        patient_id: int,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_id_and_facility(
            db,
            patient_id,
            current_user.facility_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        user = self.user_repository.get_by_id(
            db,
            patient.user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User tidak ditemukan.",
            )

        if not user.must_change_password:
            raise HTTPException(
                status_code=400,
                detail="Akun sudah diaktivasi.",
            )

        self.activation_token_repository.invalidate_user_tokens(
            db,
            user.id,
        )

        raw_token = generate_activation_token()
        token_hash = hash_activation_token(raw_token)

        activation_token = ActivationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=(datetime.utcnow() + timedelta(hours=24)),
        )

        self.activation_token_repository.create(
            db,
            activation_token,
        )

        activation_url = self._build_activation_url(raw_token)
        whatsapp_url = self._build_activation_whatsapp_url(
            patient.full_name,
            user.username,
            patient.phone,
            activation_url,
        )

        return {
            "message": "Link aktivasi baru berhasil dibuat.",
            "whatsapp_url": whatsapp_url,
        }

    # =====================================================
    # PATIENT PROFILE
    # =====================================================

    def get_profile(
        self,
        db: Session,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_user_id(
            db,
            current_user.id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient profile not found",
            )

        return patient
