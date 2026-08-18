from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes
from app.core.dependencies import require_patient
from app.models.user import User
from app.schemas.patient_detail import PatientDetailResponse
from app.services.patient_detail_service import PatientDetailService

from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientCreateResponse,
    PatientUpdate,
)

from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])

service = PatientService()
detail_service = PatientDetailService()


@router.post(
    "",
    response_model=PatientCreateResponse,
)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.create_patient(
        db,
        patient,
        current_user,
    )


@router.get(
    "",
    response_model=list[PatientResponse],
)
def get_all_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(
        db,
        current_user,
    )


def get_all_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(db)


@router.get(
    "/profile",
    response_model=PatientResponse,
)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_profile(
        db,
        current_user,
    )


@router.get(
    "/{patient_id}/detail",
    response_model=PatientDetailResponse,
)
def get_patient_detail(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return detail_service.get_detail(
        db,
        patient_id,
        current_user.facility_id,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
)
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_by_id(
        db,
        patient_id,
        current_user,
    )


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.update_patient(
        db,
        patient_id,
        patient_data,
        current_user,
    )


@router.delete(
    "/{patient_id}",
    response_model=PatientResponse,
)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.delete_patient(
        db,
        patient_id,
        current_user,
    )


def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.delete_patient(
        db,
        patient_id,
    )
