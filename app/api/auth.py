from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_admin,
)

from app.models.user import User

from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    ChangePasswordRequest,
    ChangeUsernameRequest,
    NakesCreate,
    UserResponse,
)

from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

service = AuthService()


# =====================================================
# REGISTER
# =====================================================


@router.post("/register")
def register(
    user: UserRegister,
    db: Session = Depends(get_db),
):

    return service.register(db, user)


# =====================================================
# LOGIN
# =====================================================


@router.post("/login", response_model=TokenResponse)
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):

    return service.login(db, user)


# =====================================================
# PROFILE
# =====================================================


@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user),
):

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "must_change_password": (current_user.must_change_password),
    }


# =====================================================
# CHANGE PASSWORD
# =====================================================


@router.put("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return service.change_password(
        db,
        current_user,
        password_data,
    )


# =====================================================
# CHANGE USERNAME
# =====================================================


@router.put("/change-username")
def change_username(
    username_data: ChangeUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return service.change_username(
        db,
        current_user,
        username_data.new_username,
    )


@router.post(
    "/nakes",
    response_model=UserResponse,
)
def create_nakes(
    nakes: NakesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return service.create_nakes(
        db,
        nakes,
    )
