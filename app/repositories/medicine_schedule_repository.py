from sqlalchemy.orm import Session

from app.models.medicine_schedule import MedicineSchedule


class MedicineScheduleRepository:

    def create(
        self,
        db: Session,
        schedule: MedicineSchedule,
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
            db.query(MedicineSchedule)
            .filter(
                MedicineSchedule.id == schedule_id,
                MedicineSchedule.is_active == True,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(MedicineSchedule)
            .filter(
                MedicineSchedule.is_active == True, 
            )
            .all()
        )

    def get_by_treatment(
        self,
        db: Session,
        treatment_id: int,
    ):

        return (
            db.query(MedicineSchedule)
            .filter(
                MedicineSchedule.treatment_id == treatment_id,
                MedicineSchedule.is_active == True,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        schedule: MedicineSchedule,
    ):

        db.commit()

        db.refresh(schedule)

        return schedule

    def delete(
        self,
        db: Session,
        schedule: MedicineSchedule,
    ):

        schedule.is_active = False

        db.commit()

        db.refresh(schedule)

        return schedule