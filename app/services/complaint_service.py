from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.complaint import Complaint

from app.repositories.complaint_repository import (
    ComplaintRepository,
)

from app.repositories.treatment_repository import (
    TreatmentRepository,
)

from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
)
from app.models.patient import Patient
from app.models.treatment import Treatment


class ComplaintService:

    def __init__(self):

        self.repository = ComplaintRepository()

        self.treatment_repository = TreatmentRepository()

    def create_complaint(
        self,
        db: Session,
        complaint_data: ComplaintCreate,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id(
            db,
            complaint_data.treatment_id,
        )

        if not treatment:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        # Patient hanya boleh membuat complaint
        # untuk treatment miliknya sendiri.
        if current_user.role == "patient":

            patient = (
                db.query(Patient)
                .filter(
                    Patient.user_id == current_user.id,
                    Patient.is_active.is_(True),
                )
                .first()
            )

            if not patient:
                raise HTTPException(
                    status_code=404,
                    detail="Patient profile not found",
                )

            if treatment.patient_id != patient.id:
                raise HTTPException(
                    status_code=403,
                    detail="Treatment does not belong to this patient",
                )

        complaint = Complaint(
            treatment_id=complaint_data.treatment_id,
            category=complaint_data.category,
            description=complaint_data.description,
        )

        return self.repository.create(
            db,
            complaint,
        )

        def get_all(
            self,
            db: Session,
        ):

            return self.repository.get_all(db)

        def get_by_id(
            self,
            db: Session,
            complaint_id: int,
        ):

            complaint = self.repository.get_by_id(
                db,
                complaint_id,
            )

            if not complaint:
                raise HTTPException(
                    status_code=404,
                    detail="Complaint not found",
                )

            return complaint

    def update_complaint(
        self,
        db: Session,
        complaint_id: int,
        complaint_data: ComplaintUpdate,
    ):

        complaint = self.repository.get_by_id(
            db,
            complaint_id,
        )

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        update_data = complaint_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(
                complaint,
                key,
                value,
            )

        return self.repository.update(
            db,
            complaint,
        )

    def delete_complaint(
        self,
        db: Session,
        complaint_id: int,
    ):

        complaint = self.repository.get_by_id(
            db,
            complaint_id,
        )

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        return self.repository.delete(
            db,
            complaint,
        )

    def get_my_complaints(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Complaint)
            .join(
                Treatment,
                Complaint.treatment_id == Treatment.id,
            )
            .join(
                Patient,
                Treatment.patient_id == Patient.id,
            )
            .filter(
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                Complaint.is_active.is_(True),
            )
            .order_by(
                Complaint.created_at.desc(),
            )
            .all()
        )

    def create_my_complaint(
        self,
        db: Session,
        complaint_data: ComplaintCreate,
        user_id: int,
    ):
        treatment = (
            db.query(Treatment)
            .join(
                Patient,
                Treatment.patient_id == Patient.id,
            )
            .filter(
                Treatment.id == complaint_data.treatment_id,
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
            )
            .first()
        )

        if not treatment:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found or does not belong to this patient",
            )

        complaint = Complaint(
            treatment_id=treatment.id,
            category=complaint_data.category,
            description=complaint_data.description,
        )

        return self.repository.create(
            db,
            complaint,
        )
