from datetime import date, time, timedelta
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.treatment import Treatment, TreatmentStatus
from app.models.complaint import Complaint
from app.models.medicine import Medicine
from app.models.medicine_schedule import MedicineSchedule
from app.models.daily_medication import DailyMedication, DailyMedicationStatus
from app.models.video_verification import VideoVerification
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

    def get_treatment_status_counts(
        self,
        db: Session,
    ) -> tuple[int, int]:
        active_count = (
            db.query(func.count(Treatment.id))
            .filter(
                Treatment.status == TreatmentStatus.ACTIVE,
                Treatment.is_active.is_(True),
            )
            .scalar()
            or 0
        )
        completed_count = (
            db.query(func.count(Treatment.id))
            .filter(
                Treatment.status == TreatmentStatus.COMPLETED,
                Treatment.is_active.is_(True),
            )
            .scalar()
            or 0
        )
        return active_count, completed_count

    def get_today_complaints_count(
        self,
        db: Session,
        today: date | None = None,
    ) -> int:
        if today is None:
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

    def get_today_verifications_count(
        self,
        db: Session,
        today: date,
    ) -> int:
        return (
            db.query(func.count(VideoVerification.id))
            .filter(
                or_(
                    func.date(VideoVerification.created_at) == today,
                    VideoVerification.verification_date == today,
                ),
                VideoVerification.is_active.is_(True),
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

    def get_medication_adherence_stats(
        self,
        db: Session,
        today: date,
        current_time: time,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[int, int]:
        query = (
            db.query(DailyMedication)
            .join(
                MedicineSchedule,
                MedicineSchedule.id == DailyMedication.medicine_schedule_id,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .filter(
                DailyMedication.is_active.is_(True),
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
            )
        )

        if start_date is not None:
            query = query.filter(DailyMedication.scheduled_date >= start_date)
        if end_date is not None:
            query = query.filter(DailyMedication.scheduled_date <= end_date)

        records = query.all()

        taken_count = 0
        expected_count = 0

        for record in records:
            is_expected = False
            if record.scheduled_date < today:
                is_expected = True
            elif record.scheduled_date == today:
                if record.scheduled_time <= current_time or record.status == DailyMedicationStatus.VERIFIED:
                    is_expected = True

            if is_expected:
                expected_count += 1
                if record.status == DailyMedicationStatus.VERIFIED:
                    taken_count += 1

        return taken_count, expected_count

    def get_7day_adherence_trend(
        self,
        db: Session,
        today: date,
        current_time: time,
    ) -> list[dict]:
        trend_items = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            taken, expected = self.get_medication_adherence_stats(
                db=db,
                today=today,
                current_time=current_time,
                start_date=day,
                end_date=day,
            )

            if expected > 0:
                pct = round((taken / expected) * 100.0, 1)
            else:
                pct = None

            trend_items.append({
                "date": day,
                "percentage": pct,
                "taken": taken,
                "expected": expected,
            })

        return trend_items

    def get_recent_activities(
        self,
        db: Session,
        limit: int = 5,
    ):
        activities = []

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
            patient_name = (
                complaint.treatment.patient.full_name
                if complaint.treatment and complaint.treatment.patient
                else None
            )
            title = f"Keluhan baru dari {patient_name}" if patient_name else "Keluhan baru pasien"
            activities.append(
                {
                    "type": "danger",
                    "title": title,
                    "description": complaint.description,
                    "created_at": complaint.created_at.isoformat(),
                }
            )

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
            patient_name = (
                refill.treatment.patient.full_name
                if refill.treatment and refill.treatment.patient
                else None
            )
            title = f"Permintaan refill dari {patient_name}" if patient_name else "Permintaan refill baru"
            activities.append(
                {
                    "type": "warning",
                    "title": title,
                    "description": (
                        f"Permintaan refill sebanyak "
                        f"{refill.quantity} unit. "
                        f"Status: {refill.status.value if hasattr(refill.status, 'value') else refill.status}"
                    ),
                    "created_at": refill.created_at.isoformat(),
                }
            )

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
            patient_name = (
                schedule.treatment.patient.full_name
                if schedule.treatment and schedule.treatment.patient
                else None
            )
            title = f"Jadwal kontrol baru untuk {patient_name}" if patient_name else "Jadwal kontrol baru"
            activities.append(
                {
                    "type": "primary",
                    "title": title,
                    "description": (
                        f"Jadwal kontrol "
                        f"{schedule.control_date} "
                        f"{schedule.control_time}"
                    ),
                    "created_at": schedule.created_at.isoformat(),
                }
            )

        activities.sort(
            key=lambda item: item["created_at"],
            reverse=True,
        )

        return activities[:limit]
