from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)
from app.repositories.notification_repository import NotificationRepository
from app.services.daily_medication_service import (
    jakarta_timezone,
    now_in_jakarta,
)
from app.services.notification_service import NotificationService

REMINDER_TITLE = "Pengingat Minum Obat"
REMINDER_MESSAGE = "Sudah waktunya minum obat."


def jakarta_calendar_day_utc_bounds(day: date) -> tuple[datetime, datetime]:
    zone = jakarta_timezone()
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day, time.max, tzinfo=zone)
    return (
        start.astimezone(timezone.utc).replace(tzinfo=None),
        end.astimezone(timezone.utc).replace(tzinfo=None),
    )


class MedicineReminderService:

    def __init__(self):
        self.notification_service = NotificationService()
        self.notification_repository = NotificationRepository()

    def dispatch_due_reminders(
        self,
        db: Session,
        now: datetime | None = None,
    ) -> list:
        current = now if now is not None else now_in_jakarta()
        if current.tzinfo is None:
            current = current.replace(tzinfo=jakarta_timezone())
        else:
            current = current.astimezone(jakarta_timezone())

        today = current.date()
        created_from, created_to = jakarta_calendar_day_utc_bounds(today)

        rows = (
            db.query(MedicineSchedule, Patient.user_id)
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
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
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.is_active.is_(True),
                Treatment.therapy_start_date <= today,
                Treatment.therapy_end_date >= today,
            )
            .all()
        )

        created = []
        for schedule, user_id in rows:
            scheduled_at = datetime.combine(
                today,
                schedule.drink_time,
                tzinfo=jakarta_timezone(),
            )
            if scheduled_at > current:
                continue

            if self.notification_repository.has_medicine_reminder(
                db,
                user_id,
                schedule.id,
                created_from,
                created_to,
            ):
                continue

            notification = self.notification_service.create(
                db=db,
                user_id=user_id,
                title=REMINDER_TITLE,
                message=REMINDER_MESSAGE,
                notification_type=NotificationType.MEDICINE,
                reference_type=NotificationReferenceType.MEDICINE_SCHEDULE,
                reference_id=schedule.id,
            )
            created.append(notification)

        return created
