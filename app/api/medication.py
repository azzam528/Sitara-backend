from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_patient
from app.models.user import User
from app.schemas.daily_medication import (
    PatientProgressResponse,
    TodayMedicationResponse,
)
from app.services.daily_medication_service import DailyMedicationService
from app.services.patient_progress_service import PatientProgressService

router = APIRouter(prefix="/medications", tags=["Medications"])
service = DailyMedicationService()
progress_service = PatientProgressService()


@router.get(
    "/today",
    response_model=list[TodayMedicationResponse],
)
def get_today_medications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.list_today(db, current_user)


@router.get(
    "/progress",
    response_model=PatientProgressResponse,
)
def get_medication_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return progress_service.get_progress(db, current_user)
