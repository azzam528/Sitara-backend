from sqlalchemy.orm import Session, joinedload
from app.models.patient import Patient
from app.models.user import User
from app.models.treatment import Treatment
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
            .options(joinedload(Complaint.treatment).joinedload(Treatment.patient))
            .filter(
                Complaint.id == complaint_id,
                Complaint.is_active == True,
            )
            .first()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        complaint_id: int,
        facility_id: int,
    ):
        return (
            db.query(Complaint)
            .options(joinedload(Complaint.treatment).joinedload(Treatment.patient))
            .join(
                Treatment,
                Treatment.id == Complaint.treatment_id,
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
                Complaint.id == complaint_id,
                Complaint.is_active == True,
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
            db.query(Complaint)
            .options(joinedload(Complaint.treatment).joinedload(Treatment.patient))
            .filter(
                Complaint.is_active == True,
            )
            .all()
        )

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(Complaint)
            .options(joinedload(Complaint.treatment).joinedload(Treatment.patient))
            .join(
                Treatment,
                Treatment.id == Complaint.treatment_id,
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
                Complaint.is_active == True,
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
            .options(joinedload(Complaint.treatment).joinedload(Treatment.patient))
            .filter(
                Complaint.status == ComplaintStatus.PENDING,
                Complaint.is_active == True,
            )
            .all()
        )


    def get_by_user_id(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Complaint)
            .options(
                joinedload(Complaint.treatment)
                .joinedload(Treatment.patient)
            )
            .join(
                Treatment,
                Treatment.id == Complaint.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .filter(
                Patient.user_id == user_id,
                Complaint.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
            )
            .order_by(Complaint.created_at.desc())
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

