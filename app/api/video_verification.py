from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    require_nakes,
    require_patient,
)

from app.models.user import User

from app.schemas.video_verification import (
    VideoVerificationCreate,
    VideoVerificationUpdate,
    VideoVerificationResponse,
)

from app.services.video_verification_service import (
    VideoVerificationService,
)

router = APIRouter(
    prefix="/video-verifications",
    tags=["Video Verifications"],
)

service = VideoVerificationService()


@router.post(
    "",
    response_model=VideoVerificationResponse,
)
def create_video(
    video: VideoVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.create_video(
        db,
        video,
        current_user,
    )


@router.get(
    "",
    response_model=list[VideoVerificationResponse],
)
def get_all_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(db, current_user)


@router.get(
    "/pending",
    response_model=list[VideoVerificationResponse],
)
def get_pending_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_pending(db, current_user)


@router.put(
    "/{video_id}",
    response_model=VideoVerificationResponse,
)
def update_video(
    video_id: int,
    video_data: VideoVerificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.update_video(
        db,
        video_id,
        video_data,
        current_user,
    )


@router.delete(
    "/{video_id}",
    response_model=VideoVerificationResponse,
)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.delete_video(
        db,
        video_id,
        current_user,
    )