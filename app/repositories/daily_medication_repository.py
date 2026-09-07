from datetime import date, time

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.daily_medication import (
    DailyMedication,
    DailyMedicationStatus,
)
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient
from app.models.treatment import Treatment

UPDATE_CHUNK_SIZE = 500


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

    def list_schedule_windows(
        self,
        db: Session,
        user_id: int | None = None,
    ) -> list[tuple[int, time, date, date]]:
        query = (
            db.query(
                MedicineSchedule.id,
                MedicineSchedule.drink_time,
                Treatment.therapy_start_date,
                Treatment.therapy_end_date,
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
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                Medicine.is_active.is_(True),
            )
        )
        if user_id is not None:
            query = query.filter(Patient.user_id == user_id)

        return [
            (schedule_id, drink_time, start_date, end_date)
            for schedule_id, drink_time, start_date, end_date in query.all()
        ]

    def list_existing_occurrence_keys(
        self,
        db: Session,
        schedule_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> set[tuple[int, date]]:
        if not schedule_ids:
            return set()

        keys: set[tuple[int, date]] = set()
        for offset in range(0, len(schedule_ids), UPDATE_CHUNK_SIZE):
            chunk = schedule_ids[offset:offset + UPDATE_CHUNK_SIZE]
            rows = (
                db.query(
                    DailyMedication.medicine_schedule_id,
                    DailyMedication.scheduled_date,
                )
                .filter(
                    DailyMedication.medicine_schedule_id.in_(chunk),
                    DailyMedication.scheduled_date >= start_date,
                    DailyMedication.scheduled_date <= end_date,
                )
                .all()
            )
            keys.update((schedule_id, scheduled_date) for schedule_id, scheduled_date in rows)

        return keys

    def bulk_create_occurrences(
        self,
        db: Session,
        occurrences: list[tuple[int, date, time]],
    ) -> int:
        if not occurrences:
            return 0

        try:
            db.add_all(
                [
                    DailyMedication(
                        medicine_schedule_id=schedule_id,
                        scheduled_date=scheduled_date,
                        scheduled_time=scheduled_time,
                    )
                    for schedule_id, scheduled_date, scheduled_time in occurrences
                ]
            )
            db.commit()
            return len(occurrences)
        except IntegrityError:
            db.rollback()

        created = 0
        for schedule_id, scheduled_date, scheduled_time in occurrences:
            if self.get_by_schedule_and_date(db, schedule_id, scheduled_date) is not None:
                continue
            try:
                self.create(
                    db,
                    DailyMedication(
                        medicine_schedule_id=schedule_id,
                        scheduled_date=scheduled_date,
                        scheduled_time=scheduled_time,
                    ),
                )
                created += 1
            except IntegrityError:
                db.rollback()

        return created

    def mark_due_occurrences_as_missed(
        self,
        db: Session,
        cutoff_date: date,
        user_id: int | None = None,
    ) -> int:
        query = (
            db.query(DailyMedication.id)
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
                DailyMedication.is_active.is_(True),
                DailyMedication.scheduled_date < cutoff_date,
                DailyMedication.status.in_(
                    [
                        DailyMedicationStatus.PENDING,
                        DailyMedicationStatus.IN_PROGRESS,
                    ]
                ),
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
            )
        )
        if user_id is not None:
            query = query.filter(Patient.user_id == user_id)

        occurrence_ids = [row[0] for row in query.all()]
        if not occurrence_ids:
            return 0

        updated = 0
        for offset in range(0, len(occurrence_ids), UPDATE_CHUNK_SIZE):
            chunk = occurrence_ids[offset:offset + UPDATE_CHUNK_SIZE]
            updated += (
                db.query(DailyMedication)
                .filter(DailyMedication.id.in_(chunk))
                .update(
                    {DailyMedication.status: DailyMedicationStatus.MISSED},
                    synchronize_session=False,
                )
            )
        db.commit()

        return updated

    def _due_occurrence_query(
        self,
        db: Session,
        user_id: int,
        max_date: date,
    ):
        return (
            db.query(
                DailyMedication.scheduled_date,
                DailyMedication.status,
                func.count(DailyMedication.id),
            )
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
                DailyMedication.is_active.is_(True),
                DailyMedication.scheduled_date <= max_date,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                Patient.user_id == user_id,
            )
        )

    def count_status_by_date_for_user(
        self,
        db: Session,
        user_id: int,
        max_date: date,
    ) -> list[tuple[date, DailyMedicationStatus, int]]:
        rows = (
            self._due_occurrence_query(db, user_id, max_date)
            .group_by(
                DailyMedication.scheduled_date,
                DailyMedication.status,
            )
            .all()
        )
        return [
            (scheduled_date, occurrence_status, count)
            for scheduled_date, occurrence_status, count in rows
        ]
