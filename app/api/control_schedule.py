from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    require_nakes,
    require_patient,
)

from app.models.user import User

from app.schemas.control_schedule import (
    ControlScheduleCreate,
    ControlScheduleUpdate,
    ControlScheduleResponse,
)

from app.services.control_schedule_service import (
    ControlScheduleService,
)

router = APIRouter(
    prefix="/control-schedules",
    tags=["Control Schedules"],
)

service = ControlScheduleService()


# =========================================================
# NAKES
# =========================================================


@router.post(
    "",
    response_model=ControlScheduleResponse,
)
def create_schedule(
    schedule: ControlScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.create_schedule(
        db,
        schedule,
    )


@router.get(
    "",
    response_model=list[ControlScheduleResponse],
)
def get_all_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(db)


# =========================================================
# PATIENT
# =========================================================


@router.get(
    "/my",
    response_model=list[ControlScheduleResponse],
)
def get_my_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_my_schedules(
        db,
        current_user.id,
    )


# =========================================================
# NAKES
# =========================================================


@router.get(
    "/{schedule_id}",
    response_model=ControlScheduleResponse,
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
    response_model=ControlScheduleResponse,
)
def update_schedule(
    schedule_id: int,
    schedule_data: ControlScheduleUpdate,
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
    response_model=ControlScheduleResponse,
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
