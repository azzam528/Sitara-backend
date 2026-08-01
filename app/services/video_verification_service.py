from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.video_verification import (
    VideoVerification,
    VerificationStatus,
)

from app.repositories.video_verification_repository import (
    VideoVerificationRepository,
)

from app.repositories.medicine_schedule_repository import (
    MedicineScheduleRepository,
)

from app.schemas.video_verification import (
    VideoVerificationCreate,
    VideoVerificationUpdate,
)


class VideoVerificationService:

    def __init__(self):

        self.repository = VideoVerificationRepository()

        self.schedule_repository = MedicineScheduleRepository()
        
        
    def create_video(
        self,
        db: Session,
        data: VideoVerificationCreate,
    ):

        schedule = self.schedule_repository.get_by_id(
            db,
            data.medicine_schedule_id,
        )

        if not schedule:

            raise HTTPException(
                status_code=404,
                detail="Medicine schedule not found",
            )

        video = VideoVerification(

            medicine_schedule_id=data.medicine_schedule_id,

            verification_date=data.verification_date,

            video_path=data.video_path,

            file_name=data.file_name,

            mime_type=data.mime_type,

            file_size=data.file_size,

            thumbnail_path=data.thumbnail_path,

            status=VerificationStatus.PENDING,
        )

        return self.repository.create(
            db,
            video,
        )

    def get_all(
        self,
        db: Session,
    ):

        return self.repository.get_all(db)
    
    def get_by_id(
        self,
        db: Session,
        video_id: int,
    ):

        video = self.repository.get_by_id(
            db,
            video_id,
        )

        if not video:

            raise HTTPException(
                status_code=404,
                detail="Video verification not found",
            )

        return video
    
    def update_video(
        self,
        db: Session,
        video_id: int,
        data: VideoVerificationUpdate,
    ):

        video = self.get_by_id(
            db,
            video_id,
        )

        if data.ai_confidence is not None:

            video.ai_confidence = data.ai_confidence

        if data.status is not None:

            video.status = data.status

        if data.review_note is not None:

            video.review_note = data.review_note

        return self.repository.update(
            db,
            video,
        )
        
    def delete_video(
        self,
        db: Session,
        video_id: int,
    ):

        video = self.get_by_id(
            db,
            video_id,
        )

        return self.repository.delete(
            db,
            video,
        )
        
    def get_pending(
        self,
        db: Session,
    ):

        return self.repository.get_pending(db)