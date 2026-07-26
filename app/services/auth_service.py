from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRegister, UserLogin
from app.models.user import User

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


class AuthService:

    def __init__(self):

        self.user_repository = UserRepository()
        
    def register(
        self,
        db: Session,
        user_data: UserRegister
    ):

        existing = self.user_repository.get_by_username(
            db,
            user_data.username
        )

        if existing:
            raise Exception(
                "Username already exists"
            )

        user = User(

            username=user_data.username,

            email=user_data.email,

            password_hash=hash_password(
                user_data.password
            ),

            role=user_data.role
        )

        return self.user_repository.create(
            db,
            user
        )