from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.control_schedule import (
    ControlSchedule,
    ControlScheduleStatus,
)

from app.repositories.control_schedule_repository import (
    ControlScheduleRepository,
)

from app.repositories.treatment_repository import (
    TreatmentRepository,
)

from app.schemas.control_schedule import (
    ControlScheduleCreate,
    ControlScheduleUpdate,
)

from app.models.control_schedule import ControlSchedule
from app.models.treatment import Treatment
from app.models.patient import Patient


class ControlScheduleService:

    def __init__(self):

        self.control_schedule_repository = ControlScheduleRepository()

        self.treatment_repository = TreatmentRepository()

    def create_schedule(
        self,
        db: Session,
        schedule_data: ControlScheduleCreate,
    ):

        treatment = self.treatment_repository.get_by_id(
            db,
            schedule_data.treatment_id,
        )

        if not treatment:

            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        schedule = ControlSchedule(
            treatment_id=schedule_data.treatment_id,
            control_date=schedule_data.control_date,
            control_time=schedule_data.control_time,
            doctor_note=schedule_data.doctor_note,
            status=ControlScheduleStatus.PENDING,
        )

        return self.control_schedule_repository.create(
            db,
            schedule,
        )

    def get_all(
        self,
        db: Session,
    ):

        return self.control_schedule_repository.get_all(db)

    def get_by_id(
        self,
        db: Session,
        schedule_id: int,
    ):

        schedule = self.control_schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        return schedule

    def update_schedule(
        self,
        db: Session,
        schedule_id: int,
        schedule_data: ControlScheduleUpdate,
    ):

        schedule = self.control_schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        if schedule_data.control_date is not None:

            schedule.control_date = schedule_data.control_date

        if schedule_data.control_time is not None:

            schedule.control_time = schedule_data.control_time

        if schedule_data.status is not None:

            schedule.status = schedule_data.status

        if schedule_data.doctor_note is not None:

            schedule.doctor_note = schedule_data.doctor_note

        return self.control_schedule_repository.update(
            db,
            schedule,
        )

    def delete_schedule(
        self,
        db: Session,
        schedule_id: int,
    ):

        schedule = self.control_schedule_repository.get_by_id(
            db,
            schedule_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        return self.control_schedule_repository.delete(
            db,
            schedule,
        )

    def get_my_schedules(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(ControlSchedule)
            .join(
                Treatment,
                ControlSchedule.treatment_id == Treatment.id,
            )
            .join(
                Patient,
                Treatment.patient_id == Patient.id,
            )
            .filter(
                Patient.user_id == user_id,
                Patient.is_active == True,
                Treatment.is_active == True,
                ControlSchedule.is_active == True,
            )
            .order_by(
                ControlSchedule.control_date.asc(),
                ControlSchedule.control_time.asc(),
            )
            .all()
        )
