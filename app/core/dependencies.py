from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.database import get_db
from app.core.security import verify_access_token
from app.repositories.user_repository import UserRepository

# ============================
# Bearer Authentication
# ============================

security = HTTPBearer()

user_repository = UserRepository()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):

    token = credentials.credentials

    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = user_repository.get_by_id(
        db,
        int(user_id)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# ============================
# Role Based Access Control
# ============================

def require_nakes(
    current_user: User = Depends(get_current_user),
):

    if current_user.role != "nakes":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only nakes can access this endpoint"
        )

    return current_user


def require_patient(
    current_user: User = Depends(get_current_user),
):

    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patient can access this endpoint"
        )

    return current_user

def require_nakes_or_patient(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["nakes", "patient"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only nakes or patient can access this endpoint"
        )

    return current_user