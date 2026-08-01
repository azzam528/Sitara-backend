from sqlalchemy.orm import Session

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