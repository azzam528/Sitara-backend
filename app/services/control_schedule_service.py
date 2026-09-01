from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.control_schedule import (
    ControlSchedule,
    ControlScheduleStatus,
)

from app.models.treatment import Treatment
from app.models.patient import Patient
from app.models.user import User

from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)

from app.repositories.control_schedule_repository import (
    ControlScheduleRepository,
)

from app.repositories.treatment_repository import (
    TreatmentRepository,
)

from app.services.notification_service import (
    NotificationService,
)

from app.schemas.control_schedule import (
    ControlScheduleCreate,
    ControlScheduleUpdate,
)


class ControlScheduleService:

    def __init__(self):

        self.control_schedule_repository = ControlScheduleRepository()

        self.treatment_repository = TreatmentRepository()

        self.notification_service = NotificationService()

    # =====================================================
    # CREATE
    # =====================================================

    def create_schedule(
        self,
        db: Session,
        schedule_data: ControlScheduleCreate,
        current_user: User,
    ):

        treatment = self.treatment_repository.get_by_id_and_facility(
            db,
            schedule_data.treatment_id,
            current_user.facility_id,
        )

        if not treatment:

            raise HTTPException(
                status_code=404,
                detail="Treatment not found",
            )

        # -------------------------------------------------
        # CREATE CONTROL SCHEDULE
        # -------------------------------------------------

        schedule = ControlSchedule(
            treatment_id=schedule_data.treatment_id,
            control_date=schedule_data.control_date,
            control_time=schedule_data.control_time,
            doctor_note=schedule_data.doctor_note,
            status=ControlScheduleStatus.PENDING,
        )

        schedule = self.control_schedule_repository.create(
            db,
            schedule,
        )

        # -------------------------------------------------
        # FIND PATIENT
        # -------------------------------------------------

        patient = (
            db.query(Patient)
            .filter(
                Patient.id == treatment.patient_id,
                Patient.is_active.is_(True),
            )
            .first()
        )

        if patient:

            # -------------------------------------------------
            # CREATE NOTIFICATION
            # -------------------------------------------------

            formatted_date = schedule.control_date.strftime("%d-%m-%Y")

            formatted_time = schedule.control_time.strftime("%H:%M")

            self.notification_service.create(
                db=db,
                user_id=patient.user_id,
                title="Jadwal Kontrol Baru",
                message=(
                    f"Kamu memiliki jadwal kontrol "
                    f"pada {formatted_date} "
                    f"pukul {formatted_time}."
                ),
                notification_type=(NotificationType.CONTROL),
                reference_type=(NotificationReferenceType.CONTROL_SCHEDULE),
                reference_id=schedule.id,
            )

        return schedule

    # =====================================================
    # GET ALL
    # =====================================================

    def get_all(
        self,
        db: Session,
        current_user: User,
    ):

        return self.control_schedule_repository.get_all_by_facility(db, current_user.facility_id)

    # =====================================================
    # GET BY ID
    # =====================================================

    def get_by_id(
        self,
        db: Session,
        schedule_id: int,
        current_user: User,
    ):

        schedule = self.control_schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        return schedule

    # =====================================================
    # UPDATE
    # =====================================================

    def update_schedule(
        self,
        db: Session,
        schedule_id: int,
        schedule_data: ControlScheduleUpdate,
        current_user: User,
    ):

        schedule = self.control_schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        if schedule_data.control_date is not None:

            schedule.control_date = schedule_data.control_date

        if schedule_data.control_time is not None:

            schedule.control_time = schedule_data.control_time

        if schedule_data.status is not None:

            schedule.status = schedule_data.status

        if schedule_data.doctor_note is not None:

            schedule.doctor_note = schedule_data.doctor_note

        return self.control_schedule_repository.update(
            db,
            schedule,
        )

    # =====================================================
    # DELETE
    # =====================================================

    def delete_schedule(
        self,
        db: Session,
        schedule_id: int,
        current_user: User,
    ):

        schedule = self.control_schedule_repository.get_by_id_and_facility(
            db,
            schedule_id,
            current_user.facility_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Control schedule not found",
            )

        return self.control_schedule_repository.delete(
            db,
            schedule,
        )

    # =====================================================
    # GET MY SCHEDULES
    # =====================================================

    def get_my_schedules(
        self,
        db: Session,
        user_id: int,
    ):

        return (
            db.query(ControlSchedule)
            .join(
                Treatment,
                ControlSchedule.treatment_id == Treatment.id,
            )
            .join(
                Patient,
                Treatment.patient_id == Patient.id,
            )
            .filter(
                Patient.user_id == user_id,
                Patient.is_active.is_(True),
                Treatment.is_active.is_(True),
                ControlSchedule.is_active.is_(True),
            )
            .order_by(
                ControlSchedule.control_date.asc(),
                ControlSchedule.control_time.asc(),
            )
            .all()
        )
