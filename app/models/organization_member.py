from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.enums import OrganizationRole


def utc_now():
    return datetime.now(timezone.utc)


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(
        SAEnum(OrganizationRole, name="org_role_enum", native_enum=False),
        default=OrganizationRole.TEAM_MEMBER,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")
