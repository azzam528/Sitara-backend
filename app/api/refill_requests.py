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

from app.schemas.refill_request import (
    RefillCreate,
    RefillUpdate,
    RefillResponse,
)

from app.services.refill_service import (
    RefillService,
)

router = APIRouter(
    prefix="/refills",
    tags=["Refill Requests"],
)

service = RefillService()


# =========================================================
# NAKES
# =========================================================


@router.post(
    "",
    response_model=RefillResponse,
)
def create_refill(
    refill: RefillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.create_refill(
        db,
        refill,
    )


@router.get(
    "",
    response_model=list[RefillResponse],
)
def get_all_refills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_all(db)


# =========================================================
# PATIENT
# =========================================================


@router.get(
    "/my",
    response_model=list[RefillResponse],
)
def get_my_refills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_patient),
):
    return service.get_my_refills(
        db,
        current_user.id,
    )


# =========================================================
# NAKES
# =========================================================


@router.get(
    "/{refill_id}",
    response_model=RefillResponse,
)
def get_refill(
    refill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_by_id(
        db,
        refill_id,
    )


@router.put(
    "/{refill_id}",
    response_model=RefillResponse,
)
def update_refill(
    refill_id: int,
    refill_data: RefillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.update_refill(
        db,
        refill_id,
        refill_data,
        current_user,
    )


@router.delete(
    "/{refill_id}",
    response_model=RefillResponse,
)
def delete_refill(
    refill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.delete_refill(
        db,
        refill_id,
    )
