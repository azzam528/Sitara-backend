from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_patient
from app.models.user import User
from app.schemas.daily_medication import TodayMedicationResponse
from app.services.daily_medication_service import DailyMedicationService

router = APIRouter(prefix="/medications", tags=["Medications"])
service = DailyMedicationService()


@router.get(
    "/today",
    response_model=list[TodayMedicationResponse],
)
def get_today_medications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.list_today(db, current_user)
