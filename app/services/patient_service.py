import secrets
import string

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.patient import Patient

from app.repositories.user_repository import UserRepository
from app.repositories.patient_repository import PatientRepository

from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
)

from app.core.security import hash_password


class PatientService:

    def __init__(self):

        self.user_repository = UserRepository()

        self.patient_repository = PatientRepository()


    # =====================================================
    # GET ALL
    # =====================================================

    def get_all(
        self,
        db: Session
    ):

        return self.patient_repository.get_all(db)


    # =====================================================
    # GENERATE PASSWORD
    # =====================================================

    def _generate_password(
        self,
        length: int = 10
    ):

        characters = (
            string.ascii_letters +
            string.digits
        )

        return ''.join(
            secrets.choice(characters)
            for _ in range(length)
        )


    # =====================================================
    # GENERATE USERNAME
    # =====================================================

    def _generate_username(
        self,
        db: Session,
        medical_record_number: str
    ):

        # Contoh:
        # RM-TB-2026-001
        # menjadi:
        # TB26001

        cleaned = (
            medical_record_number
            .upper()
            .replace("RM-TB-", "")
            .replace("-", "")
            .replace(" ", "")
        )

        base_username = f"TB{cleaned}"

        username = base_username

        counter = 1

        while self.user_repository.get_by_username(
            db,
            username
        ):

            username = (
                f"{base_username}{counter}"
            )

            counter += 1

        return username


    # =====================================================
    # CREATE PATIENT
    # =====================================================

    def create_patient(
        self,
        db: Session,
        patient_data: PatientCreate
    ):

        # -------------------------------------------------
        # Check NIK
        # -------------------------------------------------

        existing_nik = (
            self.patient_repository.get_by_nik(
                db,
                patient_data.nik
            )
        )

        if existing_nik:

            raise HTTPException(
                status_code=400,
                detail="NIK already exists"
            )


        # -------------------------------------------------
        # Check Medical Record Number
        # -------------------------------------------------

        existing_mrn = (
            self.patient_repository
            .get_by_medical_record_number(
                db,
                patient_data.medical_record_number
            )
        )

        if existing_mrn:

            raise HTTPException(
                status_code=400,
                detail="Medical record number already exists"
            )


        # -------------------------------------------------
        # Generate account
        # -------------------------------------------------

        username = self._generate_username(
            db,
            patient_data.medical_record_number
        )

        temporary_password = (
            self._generate_password()
        )


        # -------------------------------------------------
        # Create User
        # -------------------------------------------------

        user = User(

            username=username,

            email=None,

            password_hash=hash_password(
                temporary_password
            ),

            role="patient",

            is_active=True
        )


        user = self.user_repository.create(
            db,
            user
        )


        # -------------------------------------------------
        # Create Patient
        # -------------------------------------------------

        patient = Patient(

            user_id=user.id,

            medical_record_number=(
                patient_data.medical_record_number
            ),

            full_name=(
                patient_data.full_name
            ),

            nik=(
                patient_data.nik
            ),

            birth_date=(
                patient_data.birth_date
            ),

            gender=(
                patient_data.gender
            ),

            phone=(
                patient_data.phone
            ),

            address=(
                patient_data.address
            ),

            occupation=(
                patient_data.occupation
            ),

            pmo_name=(
                patient_data.pmo_name
            ),

            pmo_phone=(
                patient_data.pmo_phone
            ),

            clinical_note=(
                patient_data.clinical_note
            )
        )


        patient = self.patient_repository.create(
            db,
            patient
        )


        # -------------------------------------------------
        # Return patient + credentials
        # -------------------------------------------------

        return {
            "patient": patient,

            "username": username,

            "temporary_password": (
                temporary_password
            )
        }


    # =====================================================
    # GET BY ID
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        patient_id: int
    ):

        patient = (
            self.patient_repository.get_by_id(
                db,
                patient_id
            )
        )

        if patient is None:

            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return patient


    # =====================================================
    # UPDATE
    # =====================================================

    def update_patient(
        self,
        db: Session,
        patient_id: int,
        patient_data: PatientUpdate
    ):

        patient = (
            self.patient_repository.get_by_id(
                db,
                patient_id
            )
        )

        if patient is None:

            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )


        update_data = patient_data.model_dump(
            exclude_unset=True
        )


        for key, value in update_data.items():

            setattr(
                patient,
                key,
                value
            )


        return self.patient_repository.update(
            db,
            patient
        )


    # =====================================================
    # DELETE
    # =====================================================

    def delete_patient(
        self,
        db: Session,
        patient_id: int
    ):

        patient = (
            self.patient_repository.get_by_id(
                db,
                patient_id
            )
        )

        if patient is None:

            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )


        return self.patient_repository.delete(
            db,
            patient
        )


    # =====================================================
    # PATIENT PROFILE
    # =====================================================

    def get_profile(
        self,
        db: Session,
        current_user: User
    ):

        patient = (
            self.patient_repository
            .get_by_user_id(
                db,
                current_user.id
            )
        )

        if patient is None:

            raise HTTPException(
                status_code=404,
                detail="Patient profile not found"
            )

        return patient