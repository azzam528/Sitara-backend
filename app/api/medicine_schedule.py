from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes, require_patient

from app.models.user import User

from app.schemas.medicine_schedule import (
    MedicineScheduleCreate,
    MedicineScheduleUpdate,
    MedicineScheduleResponse,
    MyMedicineScheduleResponse,
)

from app.services.medicine_schedule_service import (
    MedicineScheduleService,
)

router = APIRouter(
    prefix="/medicine-schedules",
    tags=["Medicine Schedules"],
)


@router.post(
    "",
    response_model=MedicineScheduleResponse,
)
def create_schedule(
    schedule: MedicineScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.create_schedule(
        db,
        schedule,
        current_user,
    )


@router.get(
    "",
    response_model=list[MedicineScheduleResponse],
)
def get_all_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_all(db, current_user)


@router.get(
    "/my",
    response_model=list[MyMedicineScheduleResponse],
)
def get_my_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_my_schedules(
        db,
        current_user.id,
    )


@router.get(
    "/{schedule_id}",
    response_model=MedicineScheduleResponse,
)
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_by_id(
        db,
        schedule_id,
        current_user,
    )


@router.put(
    "/{schedule_id}",
    response_model=MedicineScheduleResponse,
)
def update_schedule(
    schedule_id: int,
    schedule_data: MedicineScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.update_schedule(
        db,
        schedule_id,
        schedule_data,
        current_user,
    )


@router.delete(
    "/{schedule_id}",
    response_model=MedicineScheduleResponse,
)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.delete_schedule(
        db,
        schedule_id,
        current_user,
    )


service = MedicineScheduleService()
