from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.patient import Patient
from app.models.treatment import Treatment, TreatmentStatus
from app.models.control_schedule import (
    ControlSchedule,
    ControlScheduleStatus,
)
from app.models.refill_request import RefillRequest


class PatientDetailService:

    def get_detail(
        self,
        db: Session,
        patient_id: int,
        facility_id: int,
    ):

        # ==========================================
        # 1. GET PATIENT
        # ==========================================

        patient = (
            db.query(Patient)
            .join(
                User,
                Patient.user_id == User.id,
            )
            .filter(
                Patient.id == patient_id,
                User.facility_id == facility_id,
                Patient.is_active.is_(True),
            )
            .first()
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found",
            )

        # ==========================================
        # 2. GET ACTIVE TREATMENT
        # ==========================================

        treatment = (
            db.query(Treatment)
            .filter(
                Treatment.patient_id == patient_id,
                Treatment.status == TreatmentStatus.ACTIVE,
            )
            .order_by(Treatment.created_at.desc())
            .first()
        )

        # Kalau tidak ada active treatment,
        # ambil treatment terbaru
        if treatment is None:

            treatment = (
                db.query(Treatment)
                .filter(Treatment.patient_id == patient_id)
                .order_by(Treatment.created_at.desc())
                .first()
            )

        # ==========================================
        # 3. NEXT CONTROL
        # ==========================================

        next_control = None

        if treatment is not None:

            controls = (
                db.query(ControlSchedule)
                .filter(
                    ControlSchedule.treatment_id == treatment.id,
                    ControlSchedule.status == ControlScheduleStatus.PENDING,
                    ControlSchedule.is_active == True,
                )
                .order_by(
                    ControlSchedule.control_date.asc(),
                    ControlSchedule.control_time.asc(),
                )
                .all()
            )

            now = datetime.now()

            for control in controls:

                control_datetime = datetime.combine(
                    control.control_date,
                    control.control_time,
                )

                if control_datetime >= now:
                    next_control = control
                    break

        # ==========================================
        # 4. REFILL HISTORY
        # ==========================================

        refills = []

        if treatment is not None:

            refills = (
                db.query(RefillRequest)
                .filter(
                    RefillRequest.treatment_id == treatment.id,
                    RefillRequest.is_active == True,
                )
                .order_by(RefillRequest.created_at.desc())
                .all()
            )

        # ==========================================
        # 5. RETURN
        # ==========================================

        return {
            "patient": patient,
            "treatment": treatment,
            "next_control": next_control,
            "refills": refills,
        }
