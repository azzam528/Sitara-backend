from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.user import UserRegister

from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

service = AuthService()


@router.post("/register")
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):

    return service.register(
        db,
        user
    )