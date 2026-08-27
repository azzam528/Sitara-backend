from sqlalchemy.orm import Session, joinedload

from app.models.video_verification import (
    VideoVerification,
    VerificationStatus,
)
from app.models.medicine_schedule import MedicineSchedule
from app.models.treatment import Treatment


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
            .options(
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.treatment)
                .joinedload(Treatment.patient),
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.medicine),
                joinedload(VideoVerification.face_verification),
            )
            .filter(
                VideoVerification.id == video_id,
                VideoVerification.is_active == True,
            )
            .first()
        )

    def get_all(
        self,
        db: Session,
    ):
        return (
            db.query(VideoVerification)
            .options(
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.treatment)
                .joinedload(Treatment.patient),
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.medicine),
                joinedload(VideoVerification.face_verification),
            )
            .filter(
                VideoVerification.is_active == True,
            )
            .order_by(VideoVerification.created_at.desc())
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
            .options(
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.treatment)
                .joinedload(Treatment.patient),
                joinedload(VideoVerification.medicine_schedule)
                .joinedload(MedicineSchedule.medicine),
                joinedload(VideoVerification.face_verification),
            )
            .filter(
                VideoVerification.status == VerificationStatus.PENDING,
                VideoVerification.is_active == True,
            )
            .order_by(VideoVerification.created_at.desc())
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
