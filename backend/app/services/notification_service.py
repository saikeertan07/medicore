import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import Notification

logger = logging.getLogger("medicore.notification")

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "INFO",
    link: Optional[str] = None
) -> Notification:
    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            is_read=False,
            link=link
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create notification for user {user_id}: {e}")
        return None
