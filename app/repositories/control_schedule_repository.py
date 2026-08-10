from sqlalchemy.orm import Session

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