from pydantic import BaseModel, EmailStr


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

    class Config:
        from_attributes = True