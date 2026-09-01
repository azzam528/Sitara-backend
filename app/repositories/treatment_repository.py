from sqlalchemy.orm import Session, joinedload
from app.models.patient import Patient
from app.models.user import User
from app.models.treatment import (
    Treatment,
    TreatmentStatus,
)


class TreatmentRepository:

    def create(
        self,
        db: Session,
        treatment: Treatment,
    ) -> Treatment:

        db.add(treatment)
        db.commit()
        db.refresh(treatment)

        return treatment

    def get_by_id(
        self,
        db: Session,
        treatment_id: int,
    ):
        return (
            db.query(Treatment)
            .options(joinedload(Treatment.patient))
            .filter(
                Treatment.id == treatment_id,
                Treatment.is_active == True,
            )
            .first()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        treatment_id: int,
        facility_id: int,
    ):
        return (
            db.query(Treatment)
            .options(joinedload(Treatment.patient))
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                Treatment.id == treatment_id,
                Treatment.is_active == True,
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):
        return (
            db.query(Treatment)
            .options(joinedload(Treatment.patient))
            .filter(Treatment.is_active == True)
            .all()
        )

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(Treatment)
            .options(joinedload(Treatment.patient))
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                Treatment.is_active == True,
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )

    def get_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ):

        return (
            db.query(Treatment)
            .filter(
                Treatment.patient_id == patient_id,
                Treatment.is_active == True,
            )
            .all()
        )

    def get_active_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ):

        return (
            db.query(Treatment)
            .filter(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE,
                Treatment.is_active == True,
            )
            .first()
        )

    def update(
        self,
        db: Session,
        treatment: Treatment,
    ) -> Treatment:

        db.commit()
        db.refresh(treatment)

        return treatment

    def delete(
        self,
        db: Session,
        treatment: Treatment,
    ):

        treatment.is_active = False

        db.commit()

        db.refresh(treatment)

        return treatment

    def get_my_treatments(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Treatment)
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .filter(
                Patient.user_id == user_id,
                Treatment.is_active.is_(True),
            )
            .all()
        )
