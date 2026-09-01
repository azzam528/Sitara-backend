from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes, require_patient

from app.models.user import User

from app.schemas.treatment import (
    MyTreatmentResponse,
    TreatmentCreate,
    TreatmentUpdate,
    TreatmentResponse,
)

from app.services.treatment_service import TreatmentService

router = APIRouter(
    prefix="/treatments",
    tags=["Treatments"],
)

service = TreatmentService()


@router.post(
    "",
    response_model=TreatmentResponse,
)
def create_treatment(
    treatment: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.create(
        db,
        treatment,
        current_user,
    )


@router.get(
    "",
    response_model=list[TreatmentResponse],
)
def get_all_treatments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(
        db,
        current_user,
    )


@router.get(
    "/my",
    response_model=list[MyTreatmentResponse],
)
def get_my_treatments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_my_treatments(
        db,
        current_user.id,
    )


@router.get(
    "/{treatment_id}",
    response_model=TreatmentResponse,
)
def get_treatment_by_id(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_by_id(
        db,
        treatment_id,
        current_user,
    )


@router.put(
    "/{treatment_id}",
    response_model=TreatmentResponse,
)
def update_treatment(
    treatment_id: int,
    treatment_data: TreatmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.update(
        db,
        treatment_id,
        treatment_data,
        current_user,
    )


@router.delete(
    "/{treatment_id}",
    response_model=TreatmentResponse,
)
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.delete(
        db,
        treatment_id,
        current_user,
    )
