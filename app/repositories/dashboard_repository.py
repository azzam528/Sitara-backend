from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import User
from app.models.treatment import Treatment
from app.models.complaint import Complaint
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.refill_request import RefillRequest
from app.models.control_schedule import ControlSchedule

class DashboardRepository:

    def get_active_patients_count(
        self,
        db: Session,
        facility_id: int,
    ) -> int:

        return (
            db.query(func.count(Patient.id))
            .join(User, User.id == Patient.user_id)
            .filter(
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .scalar()
            or 0
        )

    def get_today_complaints_count(
        self,
        db: Session,
        facility_id: int,
    ) -> int:

        today = date.today()

        return (
            db.query(func.count(Complaint.id))
            .join(Treatment, Treatment.id == Complaint.treatment_id)
            .join(Patient, Patient.id == Treatment.patient_id)
            .join(User, User.id == Patient.user_id)
            .filter(
                func.date(Complaint.created_at) == today,
                Complaint.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .scalar()
            or 0
        )

    def get_critical_stock(
        self,
        db: Session,
        facility_id: int,
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
            .join(Treatment, Treatment.id == MedicineSchedule.treatment_id)
            .join(Patient, Patient.id == Treatment.patient_id)
            .join(User, User.id == Patient.user_id)
            .filter(
                MedicineSchedule.is_active.is_(True),
                MedicineSchedule.quantity_remaining <= threshold,
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )
    def get_recent_activities(
        self,
        db: Session,
        facility_id: int,
        limit: int = 10,
    ):
        activities = []

        # ==========================================
        # COMPLAINTS
        # ==========================================

        complaints = (
            db.query(Complaint)
            .join(Treatment, Treatment.id == Complaint.treatment_id)
            .join(Patient, Patient.id == Treatment.patient_id)
            .join(User, User.id == Patient.user_id)
            .filter(
                Complaint.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
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
            .join(Treatment, Treatment.id == RefillRequest.treatment_id)
            .join(Patient, Patient.id == Treatment.patient_id)
            .join(User, User.id == Patient.user_id)
            .filter(
                RefillRequest.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
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
            .join(Treatment, Treatment.id == ControlSchedule.treatment_id)
            .join(Patient, Patient.id == Treatment.patient_id)
            .join(User, User.id == Patient.user_id)
            .filter(
                ControlSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
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