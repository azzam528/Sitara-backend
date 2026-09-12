from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.base import BaseSchema, BASE_SCHEMA_CONFIG


class FaceRegisterResponse(BaseModel):
    status: str = "success"
    message: str
    model_version: str


class FaceStatusResponse(BaseModel):
    is_registered: bool
    model_version: str | None = None
    registered_at: datetime | None = None

    model_config = BASE_SCHEMA_CONFIG


class FaceVerifyResponse(BaseModel):
    verified: bool
    similarity_score: float
    threshold: float
    face_verification_id: int
    status: str
    message: str

    model_config = BASE_SCHEMA_CONFIG
