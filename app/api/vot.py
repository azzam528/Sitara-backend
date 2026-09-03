from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_patient
from app.models.user import User
from app.schemas.daily_medication import (
    VotFaceVerifyResponse,
    VotMedicineDetectResponse,
    VotSessionResponse,
    VotStartRequest,
    VotStartResponse,
    VotCompleteRequest,
    VotCompleteResponse,
    VotVideoUploadResponse,
)
from app.services.vot_service import VOTService

router = APIRouter(prefix="/vot", tags=["VOT"])
service = VOTService()


@router.post(
    "/start",
    response_model=VotStartResponse,
)
def start_vot(
    payload: VotStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.start(
        db,
        current_user,
        payload.medicine_schedule_id,
    )


@router.post(
    "/face-verify",
    response_model=VotFaceVerifyResponse,
)
def vot_face_verify(
    daily_medication_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.verify_face(
        db=db,
        current_user=current_user,
        daily_medication_id=daily_medication_id,
        image=image,
    )


@router.post(
    "/medicine-detect",
    response_model=VotMedicineDetectResponse,
)
def vot_medicine_detect(
    daily_medication_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.detect_medicine(
        db=db,
        current_user=current_user,
        daily_medication_id=daily_medication_id,
        image=image,
    )


@router.post(
    "/complete",
    response_model=VotCompleteResponse,
)
def complete_vot(
    payload: VotCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.complete(
        db=db,
        current_user=current_user,
        daily_medication_id=payload.daily_medication_id,
        drinking_verified=payload.drinking_verified,
        max_drinking_stage=payload.max_drinking_stage,
        failure_reason=payload.failure_reason,
    )


@router.post(
    "/{daily_medication_id}/video",
    response_model=VotVideoUploadResponse,
)
def upload_vot_video(
    daily_medication_id: int,
    video: UploadFile = File(..., description="File video evidence proses minum obat (MP4, MOV, WebM, 3GP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.upload_video(
        db=db,
        current_user=current_user,
        daily_medication_id=daily_medication_id,
        video=video,
    )


@router.get(
    "/{daily_medication_id}",
    response_model=VotSessionResponse,
)
def get_vot_session(
    daily_medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_session(
        db,
        current_user,
        daily_medication_id,
    )
