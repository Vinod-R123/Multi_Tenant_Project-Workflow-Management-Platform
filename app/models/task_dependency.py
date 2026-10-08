from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
    )

    # The task that depends on another
    dependent_task = relationship("Task", foreign_keys=[task_id], back_populates="prerequisites")
    # The prerequisite task
    prerequisite_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="dependents")
