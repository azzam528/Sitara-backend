from sqlalchemy.orm import Session
from datetime import datetime

from app.repositories.user_repository import UserRepository
from app.repositories.activation_token_repository import (
    ActivationTokenRepository,
)

from app.schemas.user import (
    UserRegister,
    UserLogin,
    ChangePasswordRequest,
    ChangeUsernameRequest,
    ActivateAccountRequest,
    NakesCreate,
)

from app.models.user import User
from app.models.health_facility import HealthFacility

from fastapi import HTTPException, status

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    hash_activation_token,
)


class AuthService:

    def __init__(self):

        self.user_repository = UserRepository()

        self.activation_token_repository = (
            ActivationTokenRepository()
        )

    # =====================================================
    # REGISTER
    # =====================================================

    def register(
        self,
        db: Session,
        user_data: UserRegister,
    ):

        existing = self.user_repository.get_by_username(
            db,
            user_data.username,
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already exists",
            )

        # Public registration hanya untuk patient
        if user_data.role in ["admin", "nakes"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun admin/nakes hanya dapat dibuat oleh administrator.",
            )

        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            facility_id=None,
            must_change_password=False,
            is_active=True,
        )

        return self.user_repository.create(
            db,
            user,
        )

        # =====================================================

    # CREATE NAKES BY ADMIN
    # =====================================================

    def create_nakes(
        self,
        db: Session,
        nakes_data: NakesCreate,
    ):

        # =================================================
        # CHECK USERNAME
        # =================================================

        existing = self.user_repository.get_by_username(
            db,
            nakes_data.username,
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already exists",
            )

        # =================================================
        # CHECK FACILITY
        # =================================================

        facility = (
            db.query(HealthFacility)
            .filter(
                HealthFacility.id == nakes_data.facility_id,
                HealthFacility.is_active.is_(True),
            )
            .first()
        )

        if facility is None:
            raise HTTPException(
                status_code=404,
                detail="Health facility tidak ditemukan.",
            )

        # =================================================
        # CREATE NAKES
        # =================================================

        user = User(
            username=nakes_data.username,
            email=nakes_data.email,
            password_hash=hash_password(nakes_data.password),
            role="nakes",
            facility_id=nakes_data.facility_id,
            must_change_password=False,
            is_active=True,
        )

        return self.user_repository.create(
            db,
            user,
        )

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
    # ACTIVATE ACCOUNT
    # =====================================================

    def activate_account(
        self,
        db: Session,
        activation_data: ActivateAccountRequest,
    ):

        token_hash = hash_activation_token(
            activation_data.token
        )

        activation_token = (
            self.activation_token_repository
            .get_by_token_hash(
                db,
                token_hash,
            )
        )

        if activation_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link aktivasi tidak valid.",
            )

        if activation_token.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link aktivasi sudah digunakan.",
            )

        if activation_token.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=(
                    "Link aktivasi sudah kedaluwarsa. "
                    "Silakan hubungi petugas kesehatan "
                    "untuk mendapatkan link baru."
                ),
            )

        user = self.user_repository.get_by_id(
            db,
            activation_token.user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun tidak aktif.",
            )

        if user.role != "patient":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Link aktivasi hanya untuk pasien.",
            )

        if not user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Akun sudah diaktivasi.",
            )

        user.password_hash = hash_password(
            activation_data.new_password
        )

        user.must_change_password = False

        activation_token.used_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        return {
            "message": "Akun berhasil diaktivasi.",
            "username": user.username,
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

        # ================================================
        # VERIFY CURRENT PASSWORD
        # ================================================

        if not verify_password(
            password_data.current_password,
            current_user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password saat ini salah.",
            )

        # ================================================
        # PREVENT SAME PASSWORD
        # ================================================

        if verify_password(
            password_data.new_password,
            current_user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password baru tidak boleh sama dengan password lama.",
            )

        # ================================================
        # UPDATE PASSWORD
        # ================================================

        current_user.password_hash = hash_password(password_data.new_password)

        current_user.must_change_password = False

        self.user_repository.update(
            db,
            current_user,
        )

        return {
            "message": "Password berhasil diubah.",
            "must_change_password": False,
        }

        # =====================================================

    # CHANGE USERNAME
    # =====================================================

    def change_username(
        self,
        db: Session,
        current_user: User,
        new_username: str,
    ):

        new_username = new_username.strip()

        # ================================================
        # VALIDATE EMPTY
        # ================================================

        if not new_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username tidak boleh kosong.",
            )

        # ================================================
        # SAME USERNAME
        # ================================================

        if new_username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username baru sama dengan username saat ini.",
            )

        # ================================================
        # CHECK UNIQUE
        # ================================================

        existing_user = self.user_repository.get_by_username(
            db,
            new_username,
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username sudah digunakan.",
            )

        # ================================================
        # UPDATE
        # ================================================

        current_user.username = new_username

        self.user_repository.update(
            db,
            current_user,
        )

        return {
            "message": "Username berhasil diubah.",
            "username": current_user.username,
        }
