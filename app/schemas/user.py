from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    username: str
    email: str | None = None
    password: str
    role: str
    facility_id: int | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=72,
    )

    new_password: str = Field(
        min_length=8,
        max_length=72,
    )


class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(
        min_length=3,
        max_length=100,
    )


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    must_change_password: bool

    model_config = ConfigDict(from_attributes=True)


class NakesCreate(BaseModel):
    username: str
    email: str | None = None
    password: str = Field(
        min_length=8,
        max_length=72,
    )
    facility_id: int
