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
