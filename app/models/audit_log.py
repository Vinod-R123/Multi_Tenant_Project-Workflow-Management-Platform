from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)  # JSON-encoded payload
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
