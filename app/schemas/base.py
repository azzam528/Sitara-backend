from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from app.core.datetime_utils import utc_now, ensure_utc


def format_datetime_utc(dt: datetime | None) -> str | None:
    """
    Serializes a datetime object into an explicit UTC ISO 8601 string ending with 'Z'.
    Handles both naive UTC datetimes and timezone-aware datetimes.
    """
    if dt is None:
        return None
    aware = ensure_utc(dt)
    return aware.isoformat().replace("+00:00", "Z")


BASE_SCHEMA_CONFIG = ConfigDict(
    from_attributes=True,
    json_encoders={
        datetime: format_datetime_utc,
    },
)


class BaseSchema(BaseModel):
    model_config = BASE_SCHEMA_CONFIG
