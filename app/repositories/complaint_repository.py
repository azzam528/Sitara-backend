from sqlalchemy.orm import Session

from app.models.complaint import (
    Complaint,
    ComplaintStatus,
)


class ComplaintRepository:

    def create(
        self,
        db: Session,
        complaint: Complaint,
    ):

        db.add(complaint)

        db.commit()

        db.refresh(complaint)

        return complaint

    def get_by_id(
        self,
        db: Session,
        complaint_id: int,
    ):

        return (
            db.query(Complaint)
            .filter(
                Complaint.id == complaint_id,
                Complaint.is_active == True,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(Complaint)
            .filter(
                Complaint.is_active == True,
            )
            .all()
        )

    def get_by_treatment(
        self,
        db: Session,
        treatment_id: int,
    ):

        return (
            db.query(Complaint)
            .filter(
                Complaint.treatment_id == treatment_id,
                Complaint.is_active == True,
            )
            .all()
        )

    def get_pending(
        self,
        db: Session,
    ):

        return (
            db.query(Complaint)
            .filter(
                Complaint.status == ComplaintStatus.PENDING,
                Complaint.is_active == True,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        complaint: Complaint,
    ):

        db.commit()

        db.refresh(complaint)

        return complaint

    def delete(
        self,
        db: Session,
        complaint: Complaint,
    ):

        complaint.is_active = False

        db.commit()

        db.refresh(complaint)

        return complaint