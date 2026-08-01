from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes

from app.models.user import User

from app.schemas.medicine_schedule import (
    MedicineScheduleCreate,
    MedicineScheduleUpdate,
    MedicineScheduleResponse,
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
    )
    
@router.get(
    "",
    response_model=list[MedicineScheduleResponse],
)
def get_all_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_all(db)

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
    )

service = MedicineScheduleService()