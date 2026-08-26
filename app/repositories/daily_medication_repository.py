from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.daily_medication import DailyMedication
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient
from app.models.treatment import Treatment


class DailyMedicationRepository:

    def get_by_id(
        self,
        db: Session,
        daily_medication_id: int,
    ) -> DailyMedication | None:
        return (
            db.query(DailyMedication)
            .filter(
                DailyMedication.id == daily_medication_id,
                DailyMedication.is_active.is_(True),
            )
            .first()
        )

    def get_by_schedule_and_date(
        self,
        db: Session,
        medicine_schedule_id: int,
        scheduled_date: date,
    ) -> DailyMedication | None:
        return (
            db.query(DailyMedication)
            .filter(
                DailyMedication.medicine_schedule_id == medicine_schedule_id,
                DailyMedication.scheduled_date == scheduled_date,
                DailyMedication.is_active.is_(True),
            )
            .first()
        )

    def get_owned_by_id(
        self,
        db: Session,
        daily_medication_id: int,
        user_id: int,
    ) -> DailyMedication | None:
        return (
            db.query(DailyMedication)
            .join(
                MedicineSchedule,
                MedicineSchedule.id == DailyMedication.medicine_schedule_id,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .filter(
                DailyMedication.id == daily_medication_id,
                DailyMedication.is_active.is_(True),
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                MedicineSchedule.is_active.is_(True),
            )
            .first()
        )

    def get_owned_schedule_for_today(
        self,
        db: Session,
        medicine_schedule_id: int,
        user_id: int,
        today: date,
    ) -> MedicineSchedule | None:
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
            .join(
                Medicine,
                Medicine.id == MedicineSchedule.medicine_id,
            )
            .filter(
                MedicineSchedule.id == medicine_schedule_id,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Treatment.therapy_start_date <= today,
                Treatment.therapy_end_date >= today,
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Medicine.is_active.is_(True),
            )
            .first()
        )

    def list_today_schedules_for_user(
        self,
        db: Session,
        user_id: int,
        today: date,
    ) -> list[tuple[MedicineSchedule, str]]:
        results = (
            db.query(
                MedicineSchedule,
                Medicine.name,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                Medicine,
                Medicine.id == MedicineSchedule.medicine_id,
            )
            .filter(
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                Treatment.therapy_start_date <= today,
                Treatment.therapy_end_date >= today,
                MedicineSchedule.is_active.is_(True),
                Medicine.is_active.is_(True),
            )
            .order_by(MedicineSchedule.drink_time.asc())
            .all()
        )
        return [(schedule, medicine_name) for schedule, medicine_name in results]

    def create(
        self,
        db: Session,
        daily_medication: DailyMedication,
    ) -> DailyMedication:
        db.add(daily_medication)
        db.commit()
        db.refresh(daily_medication)
        return daily_medication

    def get_or_create_for_schedule_date(
        self,
        db: Session,
        schedule: MedicineSchedule,
        scheduled_date: date,
    ) -> DailyMedication:
        existing = self.get_by_schedule_and_date(
            db,
            schedule.id,
            scheduled_date,
        )
        if existing is not None:
            return existing

        occurrence = DailyMedication(
            medicine_schedule_id=schedule.id,
            scheduled_date=scheduled_date,
            scheduled_time=schedule.drink_time,
        )

        try:
            return self.create(db, occurrence)
        except IntegrityError:
            db.rollback()
            existing = self.get_by_schedule_and_date(
                db,
                schedule.id,
                scheduled_date,
            )
            if existing is None:
                raise
            return existing

    def update(
        self,
        db: Session,
        daily_medication: DailyMedication,
    ) -> DailyMedication:
        db.commit()
        db.refresh(daily_medication)
        return daily_medication
