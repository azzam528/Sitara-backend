from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_nakes

from app.models.user import User

from app.schemas.dashboard import DashboardResponse

from app.services.dashboard_service import service


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "",
    response_model=DashboardResponse,
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_nakes),
):
    return service.get_dashboard(db)