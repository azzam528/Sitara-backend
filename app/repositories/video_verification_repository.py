from sqlalchemy.orm import Session

from app.models.medicine_schedule import MedicineSchedule
from app.models.patient import Patient
from app.models.treatment import Treatment
from app.models.user import User
from app.models.video_verification import (
    VideoVerification,
    VerificationStatus,
)


class VideoVerificationRepository:

    def create(
        self,
        db: Session,
        video: VideoVerification,
    ):

        db.add(video)

        db.commit()

        db.refresh(video)

        return video

    def get_by_id(
        self,
        db: Session,
        video_id: int,
    ):

        return (
            db.query(VideoVerification)
            .filter(
                VideoVerification.id == video_id,
                VideoVerification.is_active == True,
            )
            .first()
        )

    def get_by_id_and_facility(
        self,
        db: Session,
        video_id: int,
        facility_id: int,
    ):
        return (
            db.query(VideoVerification)
            .join(
                MedicineSchedule,
                MedicineSchedule.id == VideoVerification.medicine_schedule_id,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                VideoVerification.id == video_id,
                VideoVerification.is_active == True,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):

        return (
            db.query(VideoVerification)
            .filter(
                VideoVerification.is_active == True,
            )
            .all()
        )

    def get_all_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(VideoVerification)
            .join(
                MedicineSchedule,
                MedicineSchedule.id == VideoVerification.medicine_schedule_id,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                VideoVerification.is_active == True,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )

    def get_by_schedule_id(
        self,
        db: Session,
        schedule_id: int,
    ):

        return (
            db.query(VideoVerification)
            .filter(
                VideoVerification.medicine_schedule_id == schedule_id,
                VideoVerification.is_active == True,
            )
            .all()
        )

    def get_pending(
        self,
        db: Session,
    ):

        return (
            db.query(VideoVerification)
            .filter(
                VideoVerification.status == VerificationStatus.PENDING,
                VideoVerification.is_active == True,
            )
            .all()
        )

    def get_pending_by_facility(
        self,
        db: Session,
        facility_id: int,
    ):
        return (
            db.query(VideoVerification)
            .join(
                MedicineSchedule,
                MedicineSchedule.id == VideoVerification.medicine_schedule_id,
            )
            .join(
                Treatment,
                Treatment.id == MedicineSchedule.treatment_id,
            )
            .join(
                Patient,
                Patient.id == Treatment.patient_id,
            )
            .join(
                User,
                User.id == Patient.user_id,
            )
            .filter(
                VideoVerification.status == VerificationStatus.PENDING,
                VideoVerification.is_active == True,
                MedicineSchedule.is_active.is_(True),
                Treatment.is_active.is_(True),
                Patient.is_active.is_(True),
                User.facility_id == facility_id,
            )
            .all()
        )

    def update(
        self,
        db: Session,
        video: VideoVerification,
    ):

        db.commit()

        db.refresh(video)

        return video

    def delete(
        self,
        db: Session,
        video: VideoVerification,
    ):

        video.is_active = False

        db.commit()

        db.refresh(video)

        return video