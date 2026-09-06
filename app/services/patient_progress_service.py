from datetime import date

from sqlalchemy.orm import Session

from app.models.daily_medication import DailyMedicationStatus
from app.models.user import User
from app.repositories.daily_medication_repository import (
    DailyMedicationRepository,
)
from app.schemas.daily_medication import PatientProgressResponse
from app.services.daily_medication_service import (
    DailyMedicationService,
    today_in_jakarta,
)
from app.services.occurrence_maintenance_service import (
    OccurrenceMaintenanceService,
)

FINAL_SUCCESS_STATUSES = (DailyMedicationStatus.VERIFIED,)

FINAL_FAILURE_STATUSES = (
    DailyMedicationStatus.REJECTED,
    DailyMedicationStatus.MISSED,
)


class PatientProgressService:

    def __init__(self):
        self.repository = DailyMedicationRepository()
        self.daily_medication_service = DailyMedicationService()
        self.maintenance_service = OccurrenceMaintenanceService()

    def get_progress(
        self,
        db: Session,
        current_user: User,
    ) -> PatientProgressResponse:
        self.daily_medication_service._require_active_patient(
            db,
            current_user,
        )

        self.maintenance_service.sync_for_user(db, current_user.id)

        today = today_in_jakarta()
        rows = self.repository.count_status_by_date_for_user(
            db,
            current_user.id,
            today,
        )

        successful = 0
        failed = 0
        pending_review = 0

        for _, occurrence_status, count in rows:
            if occurrence_status in FINAL_SUCCESS_STATUSES:
                successful += count
            elif occurrence_status in FINAL_FAILURE_STATUSES:
                failed += count
            elif occurrence_status == DailyMedicationStatus.NEEDS_REVIEW:
                pending_review += count

        final_due = successful + failed

        if final_due > 0:
            adherence_percentage = round((successful / final_due) * 100.0, 1)
        else:
            adherence_percentage = None

        return PatientProgressResponse(
            adherence_percentage=adherence_percentage,
            successful_occurrences=successful,
            failed_occurrences=failed,
            pending_review_occurrences=pending_review,
            final_due_occurrences=final_due,
            streak_days=self._calculate_streak_days(rows),
        )

    def _calculate_streak_days(
        self,
        rows: list[tuple[date, DailyMedicationStatus, int]],
    ) -> int:
        per_date: dict[date, dict[DailyMedicationStatus, int]] = {}
        for scheduled_date, occurrence_status, count in rows:
            per_date.setdefault(scheduled_date, {})[occurrence_status] = count

        streak = 0

        for scheduled_date in sorted(per_date, reverse=True):
            counts = per_date[scheduled_date]
            total = sum(counts.values())
            verified = counts.get(DailyMedicationStatus.VERIFIED, 0)
            final = verified + sum(
                counts.get(item, 0) for item in FINAL_FAILURE_STATUSES
            )

            # Hari yang masih menyisakan needs_review/pending/in_progress
            # belum boleh divonis patuh maupun gagal.
            if final < total:
                continue

            if verified == total:
                streak += 1
                continue

            break

        return streak
