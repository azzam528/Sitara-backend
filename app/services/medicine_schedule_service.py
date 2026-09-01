from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.medicine_schedule import MedicineSchedule
from app.models.user import User

from app.repositories.medicine_repository import MedicineRepository
from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)
from app.repositories.treatment_repository import TreatmentRepository

from app.schemas.medicine_schedule import (
    MedicineScheduleCreate,
    MedicineScheduleUpdate,
)


class MedicineScheduleService:

    def __init__(self):

        self.schedule_repository = MedicineScheduleRepository()

        self.treatment_repository = TreatmentRepository()

        self.medicine_repository = MedicineRepository()

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):
        return self.schedule_repository.get_all_by_facility(db, current_user.facility_id)

    def create_schedule(
        self,
        db: Session,
        schedule_data: MedicineScheduleCreate,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id_and_facility(
            db,
            schedule_data.treatment_id,
            current_user.facility_id,
        )

        if not treatment:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        medicine = self.medicine_repository.get_by_id(
            db,
            schedule_data.medicine_id,
        )

        if not medicine:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        existing_schedule = self.schedule_repository.get_by_treatment_and_medicine(
            db,
            schedule_data.treatment_id,
            schedule_data.medicine_id,
        )

        if existing_schedule:
            raise HTTPException(
                status_code=400,
                detail="Schedule for this medicine already exists in this treatment",
            )

        schedule = MedicineSchedule(
            treatment_id=schedule_data.treatment_id,
            medicine_id=schedule_data.medicine_id,
            dosage=schedule_data.dosage,
            quantity_initial=schedule_data.quantity_initial,
            quantity_remaining=schedule_data.quantity_initial,
            drink_time=schedule_data.drink_time,
        )

        return self.schedule_repository.create(
            db,
            schedule,
        )

    def get_by_id(
        self,
        db: Session,
        schedule_id: int,
        current_user: User,
    ):

        schedule = self.schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        return schedule

    def update_schedule(
        self,
        db: Session,
        schedule_id: int,
        schedule_data: MedicineScheduleUpdate,
        current_user: User,
    ):

        schedule = self.schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        update_data = schedule_data.model_dump(
            exclude_unset=True,
        )

        if "quantity_initial" in update_data:

            diff = update_data["quantity_initial"] - schedule.quantity_initial

            schedule.quantity_remaining += diff

            if schedule.quantity_remaining < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Resulting remaining quantity cannot be negative",
                )

        for key, value in update_data.items():
            setattr(
                schedule,
                key,
                value,
            )

        return self.schedule_repository.update(
            db,
            schedule,
        )

    def delete_schedule(
        self,
        db: Session,
        schedule_id: int,
        current_user: User,
    ):

        schedule = self.schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        return self.schedule_repository.delete(
            db,
            schedule,
        )

    # =====================================================
    # API Patient
    # =====================================================

    def get_my_schedules(
        self,
        db: Session,
        user_id: int,
    ):

        return self.schedule_repository.get_my_schedules(
            db,
            user_id,
        )

    def process_refill(
        self,
        db: Session,
        schedule_id: int,
        quantity: int,
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        schedule.quantity_remaining += quantity

        return self.schedule_repository.update(
            db,
            schedule,
        )

    def decrement_stock(
        self,
        db: Session,
        schedule_id: int,
        quantity: int = 1,
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        if schedule.quantity_remaining < quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient medicine stock",
            )

        schedule.quantity_remaining -= quantity

        return self.schedule_repository.update(
            db,
            schedule,
        )
