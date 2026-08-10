from sqlalchemy.orm import Session

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