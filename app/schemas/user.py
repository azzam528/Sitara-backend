from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    username: str
    email: str | None = None
    password: str
    role: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(
        min_length=8,
        max_length=72,
    )


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)
