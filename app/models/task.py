from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import TaskPriority, TaskStatus


def utc_now():
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    priority = Column(
        SAEnum(TaskPriority, name="task_priority_enum", native_enum=False),
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True
    )
    status = Column(
        SAEnum(TaskStatus, name="task_status_enum", native_enum=False),
        default=TaskStatus.TODO,
        nullable=False,
        index=True
    )
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    estimated_hours = Column(Numeric(8, 2), nullable=True)
    actual_hours = Column(Numeric(8, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id])
    reporter = relationship("User", foreign_keys=[reporter_id])
    
    # Dependencies: tasks that this task depends on (prerequisites)
    prerequisites = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="dependent_task",
        cascade="all, delete-orphan"
    )
    # Tasks that depend on this task
    dependents = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="prerequisite_task",
        cascade="all, delete-orphan"
    )
    
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")
