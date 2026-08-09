from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.notification_repository import (
    NotificationRepository,
)


class NotificationService:

    def __init__(self):
        self.repository = NotificationRepository()

    def get_all(
        self,
        db: Session,
        user_id: int,
    ):
        return self.repository.get_all_by_user(
            db,
            user_id,
        )

    def get_by_id(
        self,
        db: Session,
        notification_id: int,
        user_id: int,
    ):
        notification = self.repository.get_by_id(
            db,
            notification_id,
            user_id,
        )

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        return notification

    def mark_as_read(
        self,
        db: Session,
        notification_id: int,
        user_id: int,
    ):
        notification = self.get_by_id(
            db,
            notification_id,
            user_id,
        )

        if not notification.is_read:
            notification = self.repository.mark_as_read(
                db,
                notification,
            )

        return notification

    def mark_all_as_read(
        self,
        db: Session,
        user_id: int,
    ):
        return self.repository.mark_all_as_read(
            db,
            user_id,
        )

    def delete(
        self,
        db: Session,
        notification_id: int,
        user_id: int,
    ):
        notification = self.get_by_id(
            db,
            notification_id,
            user_id,
        )

        return self.repository.delete(
            db,
            notification,
        )


service = NotificationService() 