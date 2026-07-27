from pydantic import BaseModel, ConfigDict, EmailStr


class UserRegister(BaseModel):

    username: str

    email: EmailStr

    password: str

    role: str


class UserLogin(BaseModel):

    username: str

    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
