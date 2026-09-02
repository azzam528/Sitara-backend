from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin

from app.models.user import User

from app.schemas.admin import (
    AdminFacilityResponse,
    AdminNakesResponse,
)

from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

service = AdminService()


# =====================================================
# GET ALL FACILITIES
# =====================================================


@router.get(
    "/facilities",
    response_model=list[AdminFacilityResponse],
)
def get_facilities(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.get_all_facilities(db)


# =====================================================
# GET ALL NAKES
# =====================================================


@router.get(
    "/nakes",
    response_model=list[AdminNakesResponse],
)
def get_nakes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.get_all_nakes(db)
