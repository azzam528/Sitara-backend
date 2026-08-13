from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.refill_request import (
    RefillRequest,
    RefillRequestStatus,
)
from app.models.user import User
from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)

from app.repositories.refill_repository import (
    RefillRepository,
)
from app.repositories.treatment_repository import (
    TreatmentRepository,
)
from app.repositories.medicine_repository import (
    MedicineRepository,
)
from app.repositories.user_repository import (
    UserRepository,
)

from app.schemas.refill_request import (
    RefillCreate,
    RefillUpdate,
)

from app.services.notification_service import (
    NotificationService,
)


class RefillService:

    def __init__(self):

        self.refill_repository = RefillRepository()

        self.treatment_repository = TreatmentRepository()

        self.medicine_repository = MedicineRepository()

        self.user_repository = UserRepository()

        self.notification_service = NotificationService()

    # =====================================================
    # CREATE REFILL
    # NAKES + PATIENT
    # =====================================================

    def create_refill(
        self,
        db: Session,
        refill_data: RefillCreate,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id(
            db,
            refill_data.treatment_id,
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
        # CHECK MEDICINE
        # -------------------------------------------------

        medicine = self.medicine_repository.get_by_id(
            db,
            refill_data.medicine_id,
        )

        if not medicine:

            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        # -------------------------------------------------
        # CREATE REFILL
        # -------------------------------------------------

        refill = RefillRequest(
            treatment_id=refill_data.treatment_id,
            medicine_id=refill_data.medicine_id,
            quantity=refill_data.quantity,
            reason=refill_data.reason,
            description=refill_data.description,
            status=RefillRequestStatus.PENDING,
        )

        refill = self.refill_repository.create(
            db,
            refill,
        )

        # -------------------------------------------------
        # NOTIFICATION → NAKES
        # -------------------------------------------------

        if current_user.role == "patient":

            nakes_list = self.user_repository.get_all_nakes(
                db,
            )

            for nakes in nakes_list:

                self.notification_service.create(
                    db=db,
                    user_id=nakes.id,
                    title="Permintaan Refill Baru",
                    message=("Pasien mengajukan permintaan refill obat."),
                    notification_type=(NotificationType.REFILL),
                    reference_type=(NotificationReferenceType.REFILL),
                    reference_id=refill.id,
                )

        return refill

    # =====================================================
    # GET ALL
    # NAKES
    # =====================================================

    def get_all(
        self,
        db: Session,
    ):

        return self.refill_repository.get_all(db)

    # =====================================================
    # GET BY ID
    # NAKES
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        refill_id: int,
    ):

        refill = self.refill_repository.get_by_id(
            db,
            refill_id,
        )

        if not refill:

            raise HTTPException(
                status_code=404,
                detail="Refill request not found",
            )

        return refill

    # =====================================================
    # UPDATE
    # NAKES
    # =====================================================

    def update_refill(
        self,
        db: Session,
        refill_id: int,
        refill_data: RefillUpdate,
        current_user: User,
    ):

        refill = self.refill_repository.get_by_id(
            db,
            refill_id,
        )

        if not refill:

            raise HTTPException(
                status_code=404,
                detail="Refill request not found",
            )

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        if refill_data.status is not None:

            refill.status = refill_data.status

            if refill.status in [
                RefillRequestStatus.APPROVED,
                RefillRequestStatus.REJECTED,
            ]:

                refill.approved_by = current_user.id

                refill.approved_at = datetime.utcnow()

        # -------------------------------------------------
        # UPDATE NURSE NOTE
        # -------------------------------------------------

        if refill_data.nurse_note is not None:

            refill.nurse_note = refill_data.nurse_note

        refill = self.refill_repository.update(
            db,
            refill,
        )

        # -------------------------------------------------
        # NOTIFICATION → PATIENT
        # -------------------------------------------------

        if refill.status in [
            RefillRequestStatus.APPROVED,
            RefillRequestStatus.REJECTED,
        ]:

            patient = (
                db.query(Patient)
                .join(
                    Treatment,
                    Treatment.patient_id == Patient.id,
                )
                .filter(
                    Treatment.id == refill.treatment_id,
                    Patient.is_active.is_(True),
                )
                .first()
            )

            if patient:

                if refill.status == RefillRequestStatus.APPROVED:

                    title = "Refill Disetujui"

                    message = "Permintaan refill obat kamu telah disetujui."

                else:

                    title = "Refill Ditolak"

                    message = "Permintaan refill obat kamu telah ditolak."

                self.notification_service.create(
                    db=db,
                    user_id=patient.user_id,
                    title=title,
                    message=message,
                    notification_type=(NotificationType.REFILL),
                    reference_type=(NotificationReferenceType.REFILL),
                    reference_id=refill.id,
                )

        return refill

    # =====================================================
    # DELETE
    # NAKES
    # =====================================================

    def delete_refill(
        self,
        db: Session,
        refill_id: int,
    ):

        refill = self.refill_repository.get_by_id(
            db,
            refill_id,
        )

        if not refill:

            raise HTTPException(
                status_code=404,
                detail="Refill request not found",
            )

        return self.refill_repository.delete(
            db,
            refill,
        )

    # =====================================================
    # GET MY REFILLS
    # PATIENT
    # =====================================================

    def get_my_refills(
        self,
        db: Session,
        user_id: int,
    ):

        return (
            db.query(RefillRequest)
            .join(
                Treatment,
                RefillRequest.treatment_id == Treatment.id,
            )
            .join(
                Patient,
                Treatment.patient_id == Patient.id,
            )
            .filter(
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                RefillRequest.is_active.is_(True),
            )
            .order_by(
                RefillRequest.created_at.desc(),
            )
            .all()
        )
