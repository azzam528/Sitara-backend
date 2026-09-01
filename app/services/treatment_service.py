from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.treatment import (
    Treatment,
    TreatmentStatus,
)
from app.models.user import User

from app.repositories.patient_repository import PatientRepository
from app.repositories.treatment_repository import TreatmentRepository

from app.schemas.treatment import (
    TreatmentCreate,
    TreatmentUpdate,
)


class TreatmentService:

    def __init__(self):

        self.patient_repository = PatientRepository()

        self.treatment_repository = TreatmentRepository()

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):
        return self.treatment_repository.get_all_by_facility(db, current_user.facility_id)

    def create(
        self,
        db: Session,
        treatment_data: TreatmentCreate,
        current_user: User,
    ):

        patient = self.patient_repository.get_by_id_and_facility(
            db,
            treatment_data.patient_id,
            current_user.facility_id,
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        active_treatment = self.treatment_repository.get_active_by_patient_id(
            db,
            treatment_data.patient_id,
        )

        if active_treatment:
            raise HTTPException(
                status_code=400,
                detail="Patient already has an active treatment",
            )

        treatment = Treatment(
            patient_id=treatment_data.patient_id,
            diagnosis_date=treatment_data.diagnosis_date,
            therapy_start_date=treatment_data.therapy_start_date,
            therapy_end_date=treatment_data.therapy_end_date,
            phase=treatment_data.phase,
            regimen=treatment_data.regimen,
            status=TreatmentStatus.ACTIVE,
            doctor_name=treatment_data.doctor_name,
            doctor_note=treatment_data.doctor_note,
        )

        return self.treatment_repository.create(
            db,
            treatment,
        )

    def get_by_id(
        self,
        db: Session,
        treatment_id: int,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id_and_facility(
            db,
            treatment_id,
            current_user.facility_id,
        )

        if treatment is None:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        return treatment

    def get_my_treatments(
        self,
        db: Session,
        user_id: int,
    ):
        return self.treatment_repository.get_my_treatments(
            db,
            user_id,
        )

    def update(
        self,
        db: Session,
        treatment_id: int,
        treatment_data: TreatmentUpdate,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id_and_facility(
            db,
            treatment_id,
            current_user.facility_id,
        )

        if treatment is None:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        update_data = treatment_data.model_dump(
            exclude_unset=True,
        )

        for key, value in update_data.items():
            setattr(
                treatment,
                key,
                value,
            )

        return self.treatment_repository.update(
            db,
            treatment,
        )

    def delete(
        self,
        db: Session,
        treatment_id: int,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id_and_facility(
            db,
            treatment_id,
            current_user.facility_id,
        )

        if treatment is None:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        return self.treatment_repository.delete(
            db,
            treatment,
        )

