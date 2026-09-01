from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.control_schedule import (
    ControlSchedule,
    ControlScheduleStatus,
)


class ControlScheduleRepository:

    def create(
        self,
        db: Session,
        schedule: ControlSchedule,
    ):

        db.add(schedule)

        db.commit()

        db.refresh(schedule)

        return schedule

    def get_by_id(
        self,
        db: Session,
        schedule_id: int,
    ):

        return (
            db.query(ControlSchedule)
            .filter(
                ControlSchedule.id == schedule_id,
                ControlSchedule.is_active == True,
            )
            .first()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        schedule_id: int,
        facility_id: int,
    ):
        return (
            db.query(ControlSchedule)
            .join(
                Treatment,
                Treatment.id == ControlSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                ControlSchedule.id == schedule_id,
                ControlSchedule.is_active == True,
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(ControlSchedule)
            .filter(
                ControlSchedule.is_active == True,
            )
            .all()
        )

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(ControlSchedule)
            .join(
                Treatment,
                Treatment.id == ControlSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                ControlSchedule.is_active == True,
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )

    def get_by_treatment(
        self,
        db: Session,
        treatment_id: int,
    ):

        return (
            db.query(ControlSchedule)
            .filter(
                ControlSchedule.treatment_id == treatment_id,
                ControlSchedule.is_active == True,
            )
            .all()
        )

    def get_pending(
        self,
        db: Session,
    ):

        return (
            db.query(ControlSchedule)
            .filter(
                ControlSchedule.status == ControlScheduleStatus.PENDING,
                ControlSchedule.is_active == True,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        schedule: ControlSchedule,
    ):

        db.commit()

        db.refresh(schedule)

        return schedule

    def delete(
        self,
        db: Session,
        schedule: ControlSchedule,
    ):

        schedule.is_active = False

        db.commit()

        db.refresh(schedule)

        return schedule