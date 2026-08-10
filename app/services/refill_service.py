from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.refill_request import (
    RefillRequest,
    RefillRequestStatus,
)

from app.models.user import User

from app.repositories.refill_repository import (
    RefillRepository,
)

from app.repositories.treatment_repository import (
    TreatmentRepository,
)

from app.repositories.medicine_repository import (
    MedicineRepository,
)

from app.schemas.refill_request import (
    RefillCreate,
    RefillUpdate,
)


class RefillService:

    def __init__(self):

        self.refill_repository = RefillRepository()

        self.treatment_repository = TreatmentRepository()

        self.medicine_repository = MedicineRepository()

    def create_refill(
        self,
        db: Session,
        refill_data: RefillCreate,
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

        medicine = self.medicine_repository.get_by_id(
            db,
            refill_data.medicine_id,
        )

        if not medicine:

            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        refill = RefillRequest(

            treatment_id=refill_data.treatment_id,

            medicine_id=refill_data.medicine_id,

            quantity=refill_data.quantity,

            reason=refill_data.reason,

            description=refill_data.description,

            status=RefillRequestStatus.PENDING,
        )

        return self.refill_repository.create(
            db,
            refill,
        )

    def get_all(
        self,
        db: Session,
    ):

        return self.refill_repository.get_all(db)

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

        if refill_data.status is not None:

            refill.status = refill_data.status

            if refill.status in [
                RefillRequestStatus.APPROVED,
                RefillRequestStatus.REJECTED,
            ]:

                refill.approved_by = current_user.id

                refill.approved_at = datetime.utcnow()

        if refill_data.nurse_note is not None:

            refill.nurse_note = refill_data.nurse_note

        return self.refill_repository.update(
            db,
            refill,
        )

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