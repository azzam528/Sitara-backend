from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserRegister,
    UserLogin,
    ChangePasswordRequest,
)

from app.models.user import User

from fastapi import HTTPException, status

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


class AuthService:

    def __init__(self):

        self.user_repository = UserRepository()

    # =====================================================
    # REGISTER
    # =====================================================

    def register(self, db: Session, user_data: UserRegister):

        existing = self.user_repository.get_by_username(db, user_data.username)

        if existing:

            raise HTTPException(status_code=400, detail="Username already exists")

        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            must_change_password=False,
            is_active=True,
        )

        return self.user_repository.create(db, user)

    # =====================================================
    # LOGIN
    # =====================================================

    def login(self, db: Session, user_data: UserLogin):

        user = self.user_repository.get_by_username(db, user_data.username)

        if not user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah.",
            )

        if not user.is_active:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun tidak aktif.",
            )

        if not verify_password(user_data.password, user.password_hash):

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah.",
            )

        token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role,
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "must_change_password": (user.must_change_password),
        }

    # =====================================================
    # CHANGE PASSWORD
    # =====================================================

    def change_password(
        self,
        db: Session,
        current_user: User,
        password_data: ChangePasswordRequest,
    ):

        current_user.password_hash = hash_password(password_data.new_password)

        current_user.must_change_password = False

        db.commit()

        db.refresh(current_user)

        return {
            "message": "Password berhasil diubah.",
            "must_change_password": False,
        }
