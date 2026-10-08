from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import ProjectStatus


def utc_now():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        SAEnum(ProjectStatus, name="project_status_enum", native_enum=False),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True
    )
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="projects")
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="project", cascade="all, delete-orphan")
