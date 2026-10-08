import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.enums import NotificationEventType, TaskStatus
from app.models.task import Task
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def send_email_notification(to_email: str, subject: str, body: str) -> None:
    """Simulates background email dispatch"""
    logger.info(f"[EMAIL NOTIFICATION] Sending to {to_email} | Subject: {subject} | Body: {body}")


def process_overdue_tasks(db: Session) -> int:
    """Scans for overdue tasks and triggers notifications"""
    now = datetime.now(timezone.utc)
    notif_service = NotificationService(db)

    overdue_tasks = (
        db.query(Task)
        .filter(
            Task.due_date < now,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            Task.assignee_id.isnot(None)
        )
        .all()
    )

    count = 0
    for task in overdue_tasks:
        if task.assignee_id:
            notif_service.create_notification(
                organization_id=task.organization_id,
                user_id=task.assignee_id,
                event_type=NotificationEventType.TASK_OVERDUE.value,
                title="Task Overdue Warning",
                message=f"Task '{task.title}' is overdue (due {task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'N/A'})",
                entity_type="Task",
                entity_id=task.id,
            )
            count += 1

    logger.info(f"Background task processed {count} overdue task notifications")
    return count
