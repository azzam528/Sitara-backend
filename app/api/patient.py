from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
)

from app.services.patient_service import PatientService


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)

service = PatientService()


@router.post(
    "",
    response_model=PatientResponse
)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db)
):

    return service.create_patient(
        db,
        patient_data
    )