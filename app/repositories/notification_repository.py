from datetime import datetime

from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationReferenceType,
    NotificationType,
)


class NotificationRepository:

    def create(
        self,
        db: Session,
        notification: Notification,
    ):
        db.add(notification)
        db.commit()
        db.refresh(notification)

        return notification

    def get_all_by_user(
        self,
        db: Session,
        user_id: int,
    ):
        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_active.is_(True),
            )
            .order_by(
                Notification.created_at.desc()
            )
            .all()
        )

    def get_by_id(
        self,
        db: Session,
        notification_id: int,
        user_id: int,
    ):
        return (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_active.is_(True),
            )
            .first()
        )

    def mark_as_read(
        self,
        db: Session,
        notification: Notification,
    ):
        notification.is_read = True

        db.commit()
        db.refresh(notification)

        return notification

    def mark_all_as_read(
        self,
        db: Session,
        user_id: int,
    ):
        notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_active.is_(True),
                Notification.is_read.is_(False),
            )
            .all()
        )

        for notification in notifications:
            notification.is_read = True

        db.commit()

        return notifications

    def delete(
        self,
        db: Session,
        notification: Notification,
    ):
        notification.is_active = False

        db.commit()
        db.refresh(notification)

        return notification

    def has_medicine_reminder(
        self,
        db: Session,
        user_id: int,
        medicine_schedule_id: int,
        created_from: datetime,
        created_to: datetime,
    ) -> bool:
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.type == NotificationType.MEDICINE,
                Notification.reference_type
                == NotificationReferenceType.MEDICINE_SCHEDULE,
                Notification.reference_id == medicine_schedule_id,
                Notification.is_active.is_(True),
                Notification.created_at >= created_from,
                Notification.created_at <= created_to,
            )
            .first()
        )
        return existing is not None