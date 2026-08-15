from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.complaint import Complaint
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.refill_request import RefillRequest
from app.models.control_schedule import ControlSchedule

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
    def get_recent_activities(
        self,
        db: Session,
        limit: int = 10,
    ):
        activities = []

        # ==========================================
        # COMPLAINTS
        # ==========================================

        complaints = (
            db.query(Complaint)
            .filter(
                Complaint.is_active.is_(True),
            )
            .order_by(
                Complaint.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

        for complaint in complaints:
            activities.append(
                {
                    "type": "complaint",
                    "title": "Complaint baru",
                    "description": complaint.description,
                    "created_at": complaint.created_at.isoformat(),
                }
            )

        # ==========================================
        # REFILL REQUESTS
        # ==========================================

        refills = (
            db.query(RefillRequest)
            .filter(
                RefillRequest.is_active.is_(True),
            )
            .order_by(
                RefillRequest.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

        for refill in refills:
            activities.append(
                {
                    "type": "refill",
                    "title": "Permintaan refill baru",
                    "description": (
                        f"Permintaan refill sebanyak "
                        f"{refill.quantity} unit. "
                        f"Status: {refill.status.value}"
                    ),
                    "created_at": refill.created_at.isoformat(),
                }
            )

        # ==========================================
        # CONTROL SCHEDULE
        # ==========================================

        schedules = (
            db.query(ControlSchedule)
            .filter(
                ControlSchedule.is_active.is_(True),
            )
            .order_by(
                ControlSchedule.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

        for schedule in schedules:
            activities.append(
                {
                    "type": "control_schedule",
                    "title": "Jadwal kontrol baru",
                    "description": (
                        f"Jadwal kontrol "
                        f"{schedule.control_date} "
                        f"{schedule.control_time}"
                    ),
                    "created_at": schedule.created_at.isoformat(),
                }
            )

        # ==========================================
        # SORT ALL ACTIVITIES
        # ==========================================

        activities.sort(
            key=lambda item: item["created_at"],
            reverse=True,
        )

        return activities[:limit]