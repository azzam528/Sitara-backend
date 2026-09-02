from pydantic import BaseModel, ConfigDict


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
