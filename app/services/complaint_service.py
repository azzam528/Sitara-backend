from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.complaint import (
    Complaint,
    ComplaintStatus,
)
from app.models.user import User
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

        self.complaint_repository = ComplaintRepository()

        self.treatment_repository = TreatmentRepository()

        self.user_repository = UserRepository()
        self.notification_service = NotificationService()

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):
        return self.complaint_repository.get_all_by_facility(db, current_user.facility_id)

    def create_complaint(
        self,
        db: Session,
        complaint_data: ComplaintCreate,
        current_user: User,
    ):

        if current_user.role == "nakes":
            treatment = self.treatment_repository.get_by_id_and_facility(
                db,
                complaint_data.treatment_id,
                current_user.facility_id,
            )
        else:
            treatment = self.treatment_repository.get_by_id(
                db,
                complaint_data.treatment_id,
            )

        if not treatment:

            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

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
            status=ComplaintStatus.PENDING,
        )

        complaint = self.complaint_repository.create(
            db,
            complaint,
        )

        if current_user.role == "patient":
            patient_name = "Pasien"
            if hasattr(current_user, "patient") and current_user.patient and current_user.patient.full_name:
                patient_name = current_user.patient.full_name
            elif complaint.treatment and complaint.treatment.patient and complaint.treatment.patient.full_name:
                patient_name = complaint.treatment.patient.full_name

            nakes_list = self.user_repository.get_all_nakes_by_facility(
                db,
                treatment.patient.user.facility_id,
            )

            for nakes in nakes_list:

                self.notification_service.create(
                    db=db,
                    user_id=nakes.id,
                    title="Complaint Baru",
                    message=f"{patient_name} mengirim complaint baru.",
                    notification_type=NotificationType.COMPLAINT,
                    reference_type=NotificationReferenceType.COMPLAINT,
                    reference_id=complaint.id,
                )

        return complaint

    def get_by_id(
        self,
        db: Session,
        complaint_id: int,
        current_user: User,
    ):

        complaint = self.complaint_repository.get_by_id_and_facility(
            db,
            complaint_id,
            current_user.facility_id,
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
        current_user: User,
    ):

        complaint = self.complaint_repository.get_by_id_and_facility(
            db,
            complaint_id,
            current_user.facility_id,
        )

        if not complaint:

            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        if complaint_data.status is not None:

            complaint.status = complaint_data.status

            if complaint.status == ComplaintStatus.RESOLVED:

                complaint.resolved_by = current_user.id

                complaint.resolved_at = datetime.utcnow()

        if complaint_data.resolution_note is not None:

            complaint.resolution_note = complaint_data.resolution_note

        complaint = self.complaint_repository.update(
            db,
            complaint,
        )

        if complaint.status == ComplaintStatus.RESOLVED:

            patient = (
                db.query(Patient)
                .join(
                    Treatment,
                    Treatment.patient_id == Patient.id,
                )
                .filter(
                    Treatment.id == complaint.treatment_id,
                    Patient.is_active.is_(True),
                )
                .first()
            )

            if patient:

                self.notification_service.create(
                    db=db,
                    user_id=patient.user_id,
                    title="Keluhan Ditanggapi",
                    message="Keluhan kamu telah ditanggapi. Silakan cek detailnya.",
                    notification_type=(NotificationType.COMPLAINT),
                    reference_type=(NotificationReferenceType.COMPLAINT),
                    reference_id=complaint.id,
                )

        return complaint

    def delete_complaint(
        self,
        db: Session,
        complaint_id: int,
        current_user: User,
    ):

        complaint = self.complaint_repository.get_by_id_and_facility(
            db,
            complaint_id,
            current_user.facility_id,
        )

        if not complaint:

            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        return self.complaint_repository.delete(
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
