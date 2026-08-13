from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.complaint import Complaint
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule


class DashboardRepository:

    def get_active_patients_count(
        self,
        db: Session,
    ) -> int:

        return (
            db.query(func.count(Patient.id))
            .filter(
                Patient.is_active.is_(True),
            )
            .scalar()
            or 0
        )

    def get_today_complaints_count(
        self,
        db: Session,
    ) -> int:

        today = date.today()

        return (
            db.query(func.count(Complaint.id))
            .filter(
                func.date(Complaint.created_at) == today,
                Complaint.is_active.is_(True),
            )
            .scalar()
            or 0
        )

    def get_critical_stock(
        self,
        db: Session,
        threshold: int = 7,
    ):

        return (
            db.query(
                MedicineSchedule.medicine_id,
                Medicine.name,
                MedicineSchedule.quantity_remaining,
            )
            .join(
                Medicine,
                Medicine.id == MedicineSchedule.medicine_id,
            )
            .filter(
                MedicineSchedule.is_active.is_(True),
                MedicineSchedule.quantity_remaining <= threshold,
            )
            .all()
        )