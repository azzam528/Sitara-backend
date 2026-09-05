from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin

from app.models.user import User

from app.schemas.admin import (
    AdminFacilityResponse,
    AdminNakesResponse,
    FacilityCreate,
    FacilityUpdate,
    NakesUpdate,
)

from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

service = AdminService()


# =====================================================
# FACILITIES
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


@router.post(
    "/facilities",
    response_model=AdminFacilityResponse,
)
def create_facility(
    facility_data: FacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.create_facility(db, facility_data)


@router.put(
    "/facilities/{facility_id}",
    response_model=AdminFacilityResponse,
)
def update_facility(
    facility_id: int,
    facility_data: FacilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.update_facility(
        db, facility_id, facility_data,
    )


@router.delete(
    "/facilities/{facility_id}",
    response_model=AdminFacilityResponse,
)
def delete_facility(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.deactivate_facility(db, facility_id)


# =====================================================
# NAKES
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


@router.put(
    "/nakes/{nakes_id}",
    response_model=AdminNakesResponse,
)
def update_nakes(
    nakes_id: int,
    nakes_data: NakesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.update_nakes(
        db, nakes_id, nakes_data,
    )


@router.delete(
    "/nakes/{nakes_id}",
    response_model=AdminNakesResponse,
)
def delete_nakes(
    nakes_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.deactivate_nakes(db, nakes_id)
