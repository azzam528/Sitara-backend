from fastapi import HTTPException
from sqlalchemy.orm import Session

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


class ComplaintService:

    def __init__(self):

        self.repository = ComplaintRepository()

        self.treatment_repository = TreatmentRepository()

    def create_complaint(
        self,
        db: Session,
        complaint_data: ComplaintCreate,
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

        update_data = complaint_data.model_dump(
            exclude_unset=True
        )

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