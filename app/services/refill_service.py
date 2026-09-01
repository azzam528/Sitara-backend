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
    RefillResponse,
    RefillListResponse,
    PickupFacilityResponse,
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

    def _get_pickup_facility(self, current_user: User) -> PickupFacilityResponse:
        print("\n\n!!! FACILITY ID:", current_user.facility_id)
        print("!!! FACILITY:", getattr(current_user, "facility", "NO_FAC"))
        if hasattr(current_user, "facility") and current_user.facility:
            print("!!! FAC_DICT:", current_user.facility.__dict__)
            
        if not current_user.facility_id or not current_user.facility or not current_user.facility.is_active:
            raise HTTPException(
                status_code=404,
                detail="Pickup facility not found or inactive",
            )
        return PickupFacilityResponse.model_validate(current_user.facility)

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):
        refills = self.refill_repository.get_all_by_facility(db, current_user.facility_id)
        pickup_facility = self._get_pickup_facility(current_user)
        
        response = []
        for refill in refills:
            refill_data = RefillListResponse.model_validate(refill)
            refill_data.pickup_facility = pickup_facility
            response.append(refill_data.model_dump())
        
        return response

    def create_refill(
        self,
        db: Session,
        refill_data: RefillCreate,
        current_user: User,
    ):

        if current_user.role == "nakes":
            treatment = self.treatment_repository.get_by_id_and_facility(
                db,
                refill_data.treatment_id,
                current_user.facility_id,
            )
        else:
            treatment = self.treatment_repository.get_by_id(
                db,
                refill_data.treatment_id,
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
            patient_name = "Pasien"
            if hasattr(current_user, "patient") and current_user.patient and current_user.patient.full_name:
                patient_name = current_user.patient.full_name
            elif refill.treatment and refill.treatment.patient and refill.treatment.patient.full_name:
                patient_name = refill.treatment.patient.full_name

            nakes_list = self.user_repository.get_all_nakes_by_facility(
                db,
                treatment.patient.user.facility_id,
            )

            for nakes in nakes_list:

                self.notification_service.create(
                    db=db,
                    user_id=nakes.id,
                    title="Permintaan Refill Baru",
                    message=f"{patient_name} mengajukan permintaan refill obat.",
                    notification_type=NotificationType.REFILL,
                    reference_type=NotificationReferenceType.REFILL,
                    reference_id=refill.id,
                )

        response = RefillResponse.model_validate(refill)
        response.pickup_facility = self._get_pickup_facility(current_user)
        return response.model_dump()

    # =====================================================
    # GET BY ID
    # NAKES
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        refill_id: int,
        current_user: User,
    ):

        refill = self.refill_repository.get_by_id_and_facility(
            db,
            refill_id,
            current_user.facility_id,
        )

        if not refill:

            raise HTTPException(
                status_code=404,
                detail="Refill request not found",
            )

        response = RefillListResponse.model_validate(refill)
        response.pickup_facility = self._get_pickup_facility(current_user)
        return response.model_dump()

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

        refill = self.refill_repository.get_by_id_and_facility(
            db,
            refill_id,
            current_user.facility_id,
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

        response = RefillResponse.model_validate(refill)
        response.pickup_facility = self._get_pickup_facility(current_user)
        return response.model_dump()

    # =====================================================
    # DELETE
    # NAKES
    # =====================================================

    def delete_refill(
        self,
        db: Session,
        refill_id: int,
        current_user: User,
    ):

        refill = self.refill_repository.get_by_id_and_facility(
            db,
            refill_id,
            current_user.facility_id,
        )

        if not refill:

            raise HTTPException(
                status_code=404,
                detail="Refill request not found",
            )

        deleted_refill = self.refill_repository.delete(
            db,
            refill,
        )
        response = RefillResponse.model_validate(deleted_refill)
        response.pickup_facility = self._get_pickup_facility(current_user)
        return response.model_dump()

    # =====================================================
    # GET MY REFILLS
    # PATIENT
    # =====================================================

    def get_my_refills(
        self,
        db: Session,
        current_user: User,
    ):

        refills = (
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
                Patient.user_id == current_user.id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                RefillRequest.is_active.is_(True),
            )
            .order_by(
                RefillRequest.created_at.desc(),
            )
            .all()
        )

        pickup_facility = self._get_pickup_facility(current_user)
        
        response = []
        for refill in refills:
            refill_data = RefillResponse.model_validate(refill)
            refill_data.pickup_facility = pickup_facility
            response.append(refill_data.model_dump())
            
        print("DEBUG SERVICE RETURN:", response)
        return response

