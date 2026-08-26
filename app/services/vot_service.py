from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.daily_medication import DailyMedicationStatus
from app.models.medicine_schedule import MedicineSchedule
from app.models.user import User
from app.repositories.daily_medication_repository import (
    DailyMedicationRepository,
)
from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)
from app.schemas.daily_medication import (
    VotSessionResponse,
    VotStartResponse,
)
from app.services.daily_medication_service import (
    DailyMedicationService,
    today_in_jakarta,
)


class VOTService:

    def __init__(self):
        self.daily_medication_service = DailyMedicationService()
        self.repository = DailyMedicationRepository()
        self.schedule_repository = MedicineScheduleRepository()

    def start(
        self,
        db: Session,
        current_user: User,
        medicine_schedule_id: int,
    ) -> VotStartResponse:
        self.daily_medication_service._require_active_patient(
            db,
            current_user,
        )

        schedule = self.schedule_repository.get_by_id(
            db,
            medicine_schedule_id,
        )
        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine schedule not found",
            )

        today = today_in_jakarta()
        owned_schedule = self.repository.get_owned_schedule_for_today(
            db,
            medicine_schedule_id,
            current_user.id,
            today,
        )
        if owned_schedule is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Medicine schedule does not belong to this patient",
            )

        occurrence = self.repository.get_or_create_for_schedule_date(
            db,
            owned_schedule,
            today,
        )

        if occurrence.status == DailyMedicationStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT untuk jadwal obat ini hari ini sudah selesai.",
            )

        if occurrence.status in (
            DailyMedicationStatus.MISSED,
            DailyMedicationStatus.REJECTED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VOT untuk jadwal obat ini hari ini tidak dapat dimulai.",
            )

        if occurrence.status == DailyMedicationStatus.PENDING:
            occurrence.status = DailyMedicationStatus.IN_PROGRESS
            occurrence = self.repository.update(db, occurrence)

        return VotStartResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
            scheduled_date=occurrence.scheduled_date,
            scheduled_time=occurrence.scheduled_time,
        )

    def get_session(
        self,
        db: Session,
        current_user: User,
        daily_medication_id: int,
    ) -> VotSessionResponse:
        occurrence = self.daily_medication_service.get_owned(
            db,
            current_user,
            daily_medication_id,
        )
        schedule: MedicineSchedule = occurrence.medicine_schedule
        medicine_name = schedule.medicine.name if schedule.medicine else ""

        return VotSessionResponse(
            daily_medication_id=occurrence.id,
            medicine_schedule_id=occurrence.medicine_schedule_id,
            medicine_id=schedule.medicine_id,
            medicine_name=medicine_name,
            dosage=schedule.dosage,
            scheduled_date=occurrence.scheduled_date,
            scheduled_time=occurrence.scheduled_time,
            quantity_remaining=schedule.quantity_remaining,
            status=occurrence.status,
            vot_step=occurrence.vot_step,
        )
