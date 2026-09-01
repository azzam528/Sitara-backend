from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import (
    DashboardRepository,
)
from app.models.user import User


class DashboardService:

    def __init__(self):
        self.repository = DashboardRepository()

    def get_dashboard(
        self,
        db: Session,
        current_user: User,
    ):
        facility_id = current_user.facility_id

        active_patients = (
            self.repository.get_active_patients_count(db, facility_id)
        )

        today_complaints = (
            self.repository.get_today_complaints_count(db, facility_id)
        )

        critical_stock = (
            self.repository.get_critical_stock(db, facility_id)
        )

        recent_activities = (
            self.repository.get_recent_activities(db, facility_id)
        )

        return {
            "summary": {
                "active_patients": active_patients,
                "medication_adherence": 0.0,
                "high_risk_patients": 0,
                "today_complaints": today_complaints,
                "critical_stock_items": len(critical_stock),
            },

            "risk": {
                "high": 0,
                "medium": 0,
                "low": active_patients,
            },

            "adherence_trend": [],

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