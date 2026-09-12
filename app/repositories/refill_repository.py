from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.refill_request import (
    RefillRequest,
    RefillRequestStatus,
)


class RefillRepository:

    def create(
        self,
        db: Session,
        refill: RefillRequest,
    ):

        db.add(refill)

        db.commit()

        db.refresh(refill)

        return refill

    def get_by_id(
        self,
        db: Session,
        refill_id: int,
    ):

        return (
            db.query(RefillRequest)
            .filter(
                RefillRequest.id == refill_id,
                RefillRequest.is_active == True,
            )
            .first()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        refill_id: int,
        facility_id: int,
    ):
        return (
            db.query(RefillRequest)
            .join(
                Treatment,
                Treatment.id == RefillRequest.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                RefillRequest.id == refill_id,
                RefillRequest.is_active == True,
                Treatment.is_active.is_(True),
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
            db.query(RefillRequest)
            .filter(
                RefillRequest.is_active == True,
            )
            .all()
        )

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(RefillRequest)
            .join(
                Treatment,
                Treatment.id == RefillRequest.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                RefillRequest.is_active == True,
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )

    def get_by_treatment(
        self,
        db: Session,
        treatment_id: int,
    ):

        return (
            db.query(RefillRequest)
            .filter(
                RefillRequest.treatment_id == treatment_id,
                RefillRequest.is_active == True,
            )
            .all()
        )

    def get_pending(
        self,
        db: Session,
    ):

        return (
            db.query(RefillRequest)
            .filter(
                RefillRequest.status == RefillRequestStatus.PENDING,
                RefillRequest.is_active == True,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        refill: RefillRequest,
    ):

        db.commit()

        db.refresh(refill)

        return refill

    def delete(
        self,
        db: Session,
        refill: RefillRequest,
    ):

        refill.is_active = False

        db.commit()

        db.refresh(refill)

        return refill