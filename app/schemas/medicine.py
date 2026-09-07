from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.base import BaseSchema, BASE_SCHEMA_CONFIG


class MedicineCreate(BaseModel):

    code: str = Field(max_length=20)

    name: str = Field(max_length=100)

    category: str = Field(max_length=50)

    strength: str = Field(max_length=100)

    unit: str = Field(max_length=20)

    description: str | None = None


class MedicineUpdate(BaseModel):

    code: str

    name: str

    category: str

    strength: str

    unit: str

    description: str | None = None


class MedicineResponse(BaseModel):

    id: int

    code: str

    name: str

    category: str

    strength: str

    unit: str

    description: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = BASE_SCHEMA_CONFIG