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

    service = MedicineReminderService()
    while True:
        db = SessionLocal()
        try:
            service.dispatch_due_reminders(db)
        except Exception:
            logger.exception("Medicine reminder dispatch failed")
        finally:
            db.close()
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
