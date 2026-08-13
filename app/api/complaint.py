from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    require_nakes,
    require_nakes_or_patient,
)

from app.models.user import User

from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
)

from app.services.complaint_service import (
    ComplaintService,
)

router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)

service = ComplaintService()


@router.post(
    "",
    response_model=ComplaintResponse,
)
def create_complaint(
    complaint: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes_or_patient),
):

    return service.create_complaint(
        db,
        complaint,
        current_user,
    )

@router.get(
    "",
    response_model=list[ComplaintResponse],
)
def get_all_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_all(db)


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.get_by_id(
        db,
        complaint_id,
    )


@router.put(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def update_complaint(
    complaint_id: int,
    complaint_data: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.update_complaint(
        db,
        complaint_id,
        complaint_data,
    )


@router.delete(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def delete_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):

    return service.delete_complaint(
        db,
        complaint_id,
    )