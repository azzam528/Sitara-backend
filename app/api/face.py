from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_patient
from app.models.user import User
from app.schemas.face import FaceRegisterResponse, FaceStatusResponse, FaceVerifyResponse
from app.services.face_service import FaceService

router = APIRouter(prefix="/face", tags=["Face Recognition"])
service = FaceService()


@router.post(
    "/register",
    response_model=FaceRegisterResponse,
    summary="Register patient face embedding",
    description="Registers the authenticated patient's face by detecting a single face and extracting a 128-D embedding vector.",
)
def register_face(
    image: UploadFile = File(..., description="Foto wajah pasien (JPG/PNG/WEBP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.register_face(
        db=db,
        current_user=current_user,
        image=image,
    )


@router.post(
    "/verify",
    response_model=FaceVerifyResponse,
    summary="Verify patient face identity",
    description="Verifies patient face identity against registered active embedding before AI-VOT medication intake session.",
)
def verify_face(
    image: UploadFile = File(..., description="Foto wajah pasien (JPG/PNG/WEBP)"),
    medicine_schedule_id: int = Form(..., description="ID Jadwal minum obat pasien"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.verify_face(
        db=db,
        current_user=current_user,
        image=image,
        medicine_schedule_id=medicine_schedule_id,
    )


@router.get(
    "/status",
    response_model=FaceStatusResponse,
    summary="Get patient face registration status",
    description="Checks whether the authenticated patient has an active registered face embedding in the system.",
)
def get_face_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_face_status(
        db=db,
        current_user=current_user,
    )

