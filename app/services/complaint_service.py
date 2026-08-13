from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.complaint import Complaint

from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)

from app.repositories.complaint_repository import (
    ComplaintRepository,
)

from app.repositories.treatment_repository import (
    TreatmentRepository,
)

from app.repositories.user_repository import (
    UserRepository,
)

from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
)

from app.services.notification_service import (
    NotificationService,
)


class ComplaintService:

    def __init__(self):

        self.repository = ComplaintRepository()

        self.treatment_repository = TreatmentRepository()

        self.user_repository = UserRepository()

        self.notification_service = NotificationService()

    # =====================================================
    # CREATE COMPLAINT
    # NAKES + PATIENT
    # =====================================================

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

        # -------------------------------------------------
        # PATIENT OWNERSHIP CHECK
        # -------------------------------------------------

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

        # -------------------------------------------------
        # CREATE COMPLAINT
        # -------------------------------------------------

        complaint = Complaint(
            treatment_id=complaint_data.treatment_id,
            category=complaint_data.category,
            description=complaint_data.description,
        )

        complaint = self.repository.create(
            db,
            complaint,
        )

        # -------------------------------------------------
        # NOTIFICATION
        #
        # Hanya ketika PATIENT membuat complaint,
        # notify semua Nakes aktif.
        # -------------------------------------------------

        if current_user.role == "patient":

            nakes_list = self.user_repository.get_all_nakes(
                db,
            )

            for nakes in nakes_list:

                self.notification_service.create(
                    db=db,
                    user_id=nakes.id,
                    title="Complaint Baru",
                    message="Pasien mengirim complaint baru.",
                    notification_type=NotificationType.COMPLAINT,
                    reference_type=NotificationReferenceType.COMPLAINT,
                    reference_id=complaint.id,
                )

            return complaint

    # =====================================================
    # GET ALL
    # NAKES
    # =====================================================

    def get_all(
        self,
        db: Session,
    ):

        return self.repository.get_all(db)

    # =====================================================
    # GET BY ID
    # NAKES
    # =====================================================

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

    # =====================================================
    # UPDATE
    # NAKES
    # =====================================================

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
            exclude_unset=True,
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

    # =====================================================
    # DELETE
    # NAKES
    # =====================================================

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

    # =====================================================
    # GET MY COMPLAINTS
    # PATIENT
    # =====================================================

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
