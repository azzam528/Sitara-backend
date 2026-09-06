from pydantic import BaseModel, ConfigDict, Field


class AdminFacilityResponse(BaseModel):
    id: int
    name: str
    address: str | None
    phone: str | None
    latitude: float | None
    longitude: float | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AdminNakesResponse(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    facility_id: int | None
    facility_name: str | None

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# FACILITY REQUEST SCHEMAS
# =====================================================


class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=20)
    latitude: float | None = None
    longitude: float | None = None


class FacilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


# =====================================================
# NAKES REQUEST SCHEMAS
# =====================================================


class NakesUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=100,
    )
    email: str | None = None
    facility_id: int | None = None
    is_active: bool | None = None
