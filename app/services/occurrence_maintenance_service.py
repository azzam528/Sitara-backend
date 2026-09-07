from datetime import date, time, timedelta

from sqlalchemy.orm import Session

from app.repositories.daily_medication_repository import (
    DailyMedicationRepository,
)
from app.services.daily_medication_service import today_in_jakarta

# Occurrence hanya dibuat untuk tanggal yang sudah lewat (bukan masa depan).
# Batas ini menjaga jumlah row tetap wajar untuk terapi yang sangat panjang.
MAX_BACKFILL_DAYS = 400

# Loop background hanya perlu menutup celah beberapa hari terakhir,
# karena backfill penuh sudah dilakukan saat pasien membuka progress.
RECENT_BACKFILL_DAYS = 7


class OccurrenceMaintenanceService:

    def __init__(self):
        self.repository = DailyMedicationRepository()

    def sync_for_user(
        self,
        db: Session,
        user_id: int,
    ) -> tuple[int, int]:
        return self._sync(
            db,
            user_id=user_id,
            lookback_days=MAX_BACKFILL_DAYS,
        )

    def sync_recent(
        self,
        db: Session,
    ) -> tuple[int, int]:
        return self._sync(
            db,
            user_id=None,
            lookback_days=RECENT_BACKFILL_DAYS,
        )

    def _sync(
        self,
        db: Session,
        user_id: int | None,
        lookback_days: int,
    ) -> tuple[int, int]:
        today = today_in_jakarta()
        last_due_date = today - timedelta(days=1)
        window_start = today - timedelta(days=lookback_days)

        created = self._backfill_due_occurrences(
            db,
            user_id=user_id,
            window_start=window_start,
            last_due_date=last_due_date,
        )

        missed = self.repository.mark_due_occurrences_as_missed(
            db,
            cutoff_date=today,
            user_id=user_id,
        )

        return created, missed

    def _backfill_due_occurrences(
        self,
        db: Session,
        user_id: int | None,
        window_start: date,
        last_due_date: date,
    ) -> int:
        windows = self.repository.list_schedule_windows(db, user_id)
        if not windows:
            return 0

        planned: list[tuple[int, date, time]] = []
        schedule_ids: list[int] = []
        earliest: date | None = None

        for schedule_id, drink_time, therapy_start, therapy_end in windows:
            first_date = max(therapy_start, window_start)
            last_date = min(therapy_end, last_due_date)
            if first_date > last_date:
                continue

            schedule_ids.append(schedule_id)
            if earliest is None or first_date < earliest:
                earliest = first_date

            current = first_date
            while current <= last_date:
                planned.append((schedule_id, current, drink_time))
                current += timedelta(days=1)

        if not planned or earliest is None:
            return 0

        existing = self.repository.list_existing_occurrence_keys(
            db,
            schedule_ids,
            earliest,
            last_due_date,
        )

        missing = [
            item
            for item in planned
            if (item[0], item[1]) not in existing
        ]

        return self.repository.bulk_create_occurrences(db, missing)
