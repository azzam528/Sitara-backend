from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.daily_medication import DailyMedication
from app.models.user import User
from app.repositories.daily_medication_repository import (
    DailyMedicationRepository,
)
from app.repositories.patient_repository import PatientRepository
from app.schemas.daily_medication import TodayMedicationResponse


def jakarta_timezone():
    try:
        return ZoneInfo("Asia/Jakarta")
    except ZoneInfoNotFoundError:
        # Windows CPython may lack IANA tz data; Jakarta is UTC+7 year-round.
        return timezone(timedelta(hours=7))


def today_in_jakarta() -> date:
    return datetime.now(jakarta_timezone()).date()


class DailyMedicationService:

    def __init__(self):
        self.repository = DailyMedicationRepository()
        self.patient_repository = PatientRepository()

    def _require_active_patient(self, db: Session, current_user: User):
        patient = self.patient_repository.get_by_user_id(
            db,
            current_user.id,
        )
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data profil pasien tidak ditemukan untuk pengguna ini.",
            )
        return patient

    def list_today(
        self,
        db: Session,
        current_user: User,
    ) -> list[TodayMedicationResponse]:
        self._require_active_patient(db, current_user)
        today = today_in_jakarta()

        schedules = self.repository.list_today_schedules_for_user(
            db,
            current_user.id,
            today,
        )

        items: list[TodayMedicationResponse] = []
        for schedule, medicine_name in schedules:
            occurrence = self.repository.get_or_create_for_schedule_date(
                db,
                schedule,
                today,
            )
            items.append(
                TodayMedicationResponse(
                    daily_medication_id=occurrence.id,
                    medicine_schedule_id=schedule.id,
                    medicine_id=schedule.medicine_id,
                    medicine_name=medicine_name,
                    dosage=schedule.dosage,
                    scheduled_date=occurrence.scheduled_date,
                    scheduled_time=occurrence.scheduled_time,
                    quantity_remaining=schedule.quantity_remaining,
                    status=occurrence.status,
                    vot_step=occurrence.vot_step,
                )
            )

        return items

    def get_owned(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
    ) -> DailyMedication:
        self._require_active_patient(db, current_user)
        occurrence = self.repository.get_owned_by_id(
            db,
            daily_medication_id,
            current_user.id,
        )
        if occurrence is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily medication not found",
            )
        return occurrence
