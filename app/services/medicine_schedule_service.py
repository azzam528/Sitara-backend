from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.medicine_schedule import MedicineSchedule

from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)
from app.repositories.treatment_repository import (
    TreatmentRepository,
)
from app.repositories.medicine_repository import (
    MedicineRepository,
)

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
    ):

        return self.schedule_repository.get_all(db)

    def create_schedule(
        self,
        db: Session,
        schedule_data: MedicineScheduleCreate,
    ):

        treatment = self.treatment_repository.get_by_id(
            db,
            schedule_data.treatment_id,
        )

        if treatment is None:
            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        medicine = self.medicine_repository.get_by_id(
            db,
            schedule_data.medicine_id,
        )

        if medicine is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found",
            )

        existing = self.schedule_repository.get_by_treatment_and_medicine(
            db,
            schedule_data.treatment_id,
            schedule_data.medicine_id,
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Medicine schedule already exists",
            )

        schedule = MedicineSchedule(
            treatment_id=schedule_data.treatment_id,
            medicine_id=schedule_data.medicine_id,
            dosage=schedule_data.dosage,
            quantity_initial=schedule_data.quantity_initial,
            quantity_remaining=schedule_data.quantity_remaining,
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
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if schedule is None:
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
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if schedule is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        update_data = schedule_data.model_dump(
            exclude_unset=True,
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
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if schedule is None:
            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        return self.schedule_repository.delete(
            db,
            schedule,
        )

    def get_my_schedules(
        self,
        db: Session,
        user_id: int,
    ):
        return self.schedule_repository.get_my_schedules(
            db,
            user_id,
        )
