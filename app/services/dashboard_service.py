from datetime import date, datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import (
    DashboardRepository,
)
from app.models.user import User


def jakarta_timezone():
    try:
        return ZoneInfo("Asia/Jakarta")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=7))


def today_in_jakarta() -> date:
    return datetime.now(jakarta_timezone()).date()


def now_time_in_jakarta() -> time:
    return datetime.now(jakarta_timezone()).time()


class DashboardService:

    def __init__(self):
        self.repository = DashboardRepository()

    def get_dashboard(
        self,
        db: Session,
        current_user: User,
    ):
        facility_id = current_user.facility_id
        today = today_in_jakarta()
        current_time = now_time_in_jakarta()
        start_7d = today - timedelta(days=6)

        active_patients = (
            self.repository.get_active_patients_count(db, facility_id)
        )

        active_treatments, completed_treatments = (
            self.repository.get_treatment_status_counts(db, facility_id)
        )

        today_verifications = (
            self.repository.get_today_verifications_count(db, today=today, facility_id=facility_id)
        )

        today_complaints = (
            self.repository.get_today_complaints_count(db, facility_id=facility_id, today=today)
        )

        critical_stock = (
            self.repository.get_critical_stock(db, facility_id)
        )

        recent_activities = (
            self.repository.get_recent_activities(db, facility_id)
        )

        taken_7d, expected_7d = self.repository.get_medication_adherence_stats(
            db=db,
            today=today,
            current_time=current_time,
            start_date=start_7d,
            end_date=today,
            facility_id=facility_id,
        )

        if expected_7d > 0:
            overall_adherence = round((taken_7d / expected_7d) * 100.0, 1)
        else:
            taken_all, expected_all = self.repository.get_medication_adherence_stats(
                db=db,
                today=today,
                current_time=current_time,
                facility_id=facility_id,
            )
            if expected_all > 0:
                overall_adherence = round((taken_all / expected_all) * 100.0, 1)
            else:
                overall_adherence = None

        adherence_trend = self.repository.get_7day_adherence_trend(
            db=db,
            today=today,
            current_time=current_time,
            facility_id=facility_id,
        )

        return {
            "summary": {
                "active_patients": active_patients,
                "active_treatments": active_treatments,
                "completed_treatments": completed_treatments,
                "medication_adherence": overall_adherence,
                "today_verifications": today_verifications,
                "today_complaints": today_complaints,
                "critical_stock_items": len(critical_stock),
                "high_risk_patients": 0,
                "tb_ro_patients": 0,
            },

            "risk": {
                "high": 0,
                "medium": 0,
                "low": active_patients,
            },

            "adherence_trend": adherence_trend,

            "recent_activities": recent_activities,

            "critical_stock": [
                {
                    "medicine_id": item.medicine_id,
                    "medicine_name": item.name,
                    "quantity_remaining": item.quantity_remaining,
                }
                for item in critical_stock
            ],
        }


service = DashboardService()
