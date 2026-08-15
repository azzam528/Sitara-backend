from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import (
    DashboardRepository,
)


class DashboardService:

    def __init__(self):
        self.repository = DashboardRepository()

    def get_dashboard(
        self,
        db: Session,
    ):

        active_patients = (
            self.repository.get_active_patients_count(db)
        )

        today_complaints = (
            self.repository.get_today_complaints_count(db)
        )

        critical_stock = (
            self.repository.get_critical_stock(db)
        )

        recent_activities = (
            self.repository.get_recent_activities(db)
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