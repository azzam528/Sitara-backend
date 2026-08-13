from sqlalchemy.orm import Session

from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient
from app.models.treatment import Treatment


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

    def get_by_treatment_and_medicine(
        self,
        db: Session,
        treatment_id: int,
        medicine_id: int,
    ):

        return (
            db.query(MedicineSchedule)
            .filter(
                MedicineSchedule.treatment_id == treatment_id,
                MedicineSchedule.medicine_id == medicine_id,
                MedicineSchedule.is_active == True,
            )
            .first()
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

    def get_my_schedules(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(MedicineSchedule)
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .filter(
                Patient.user_id == user_id,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
            )
            .all()
        )
