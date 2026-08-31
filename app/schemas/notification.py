from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.notification import (
    NotificationType,
    NotificationReferenceType,
)


class NotificationResponse(BaseModel):

    id: int
    user_id: int

    title: str
    message: str

    type: NotificationType

    reference_type: NotificationReferenceType | None = None
    reference_id: int | None = None

    is_read: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime_utc(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")