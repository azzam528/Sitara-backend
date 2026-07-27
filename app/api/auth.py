from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.schemas.user import UserRegister

from app.services.auth_service import AuthService
from app.schemas.user import UserLogin, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

service = AuthService()


@router.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):

    return service.register(db, user)


@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):

    return service.login(db, user)
