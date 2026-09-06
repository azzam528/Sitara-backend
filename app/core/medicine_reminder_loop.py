import asyncio
import logging
import os

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 60


def reminder_loop_enabled() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith("sqlite"):
        return False
    return True


async def medicine_reminder_loop() -> None:
    from app.core.database import SessionLocal
    from app.services.medicine_reminder_service import MedicineReminderService
    from app.services.occurrence_maintenance_service import (
        OccurrenceMaintenanceService,
    )

    service = MedicineReminderService()
    maintenance_service = OccurrenceMaintenanceService()
    while True:
        db = SessionLocal()
        try:
            try:
                service.dispatch_due_reminders(db)
            except Exception:
                logger.exception("Medicine reminder dispatch failed")

            try:
                maintenance_service.sync_recent(db)
            except Exception:
                logger.exception("Daily medication occurrence maintenance failed")
        finally:
            db.close()
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
