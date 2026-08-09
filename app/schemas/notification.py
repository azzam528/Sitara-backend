from datetime import datetime

from pydantic import BaseModel, ConfigDict

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