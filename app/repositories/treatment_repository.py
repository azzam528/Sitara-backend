from sqlalchemy.orm import Session

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
            .filter(
                Treatment.id == treatment_id,
                Treatment.is_active == True,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(Treatment)
            .filter(
                Treatment.is_active == True
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
        
    