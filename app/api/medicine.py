from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes

from app.models.user import User

from app.schemas.medicine import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
)

from app.services.medicine_service import MedicineService


router = APIRouter(
    prefix="/medicines",
    tags=["Medicines"],
)

service = MedicineService()


@router.post(
    "",
    response_model=MedicineResponse,
)
def create_medicine(
    medicine: MedicineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.create_medicine(
        db,
        medicine,
    )


@router.get(
    "",
    response_model=list[MedicineResponse],
)
def get_all_medicines(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_all(db)


@router.get(
    "/{medicine_id}",
    response_model=MedicineResponse,
)
def get_medicine_by_id(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_by_id(
        db,
        medicine_id,
    )


@router.put(
    "/{medicine_id}",
    response_model=MedicineResponse,
)
def update_medicine(
    medicine_id: int,
    medicine_data: MedicineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.update_medicine(
        db,
        medicine_id,
        medicine_data,
    )


@router.delete(
    "/{medicine_id}",
    response_model=MedicineResponse,
)
def delete_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.delete_medicine(
        db,
        medicine_id,
    )