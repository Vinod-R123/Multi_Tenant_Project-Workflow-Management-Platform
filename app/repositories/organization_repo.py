from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.enums import OrganizationRole
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: Session):
        super().__init__(Organization, db)

    def get_by_slug(self, slug: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def list_user_organizations(self, user_id: int) -> List[Tuple[Organization, OrganizationMember]]:
        query = (
            self.db.query(Organization, OrganizationMember)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .filter(
                OrganizationMember.user_id == user_id,
                Organization.is_active == True,
            )
        )
        return query.all()

    def get_member(self, organization_id: int, user_id: int) -> Optional[OrganizationMember]:
        return (
            self.db.query(OrganizationMember)
            .options(joinedload(OrganizationMember.user))
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            .first()
        )

    def add_member(
        self,
        organization_id: int,
        user_id: int,
        role: OrganizationRole = OrganizationRole.TEAM_MEMBER,
        is_active: bool = True
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            is_active=is_active,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, organization_id: int, user_id: int) -> bool:
        member = self.get_member(organization_id, user_id)
        if member:
            self.db.delete(member)
            self.db.commit()
            return True
        return False

    def list_members(
        self,
        organization_id: int,
        skip: int = 0,
        limit: int = 20,
        role: Optional[OrganizationRole] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[OrganizationMember], int]:
        query = (
            self.db.query(OrganizationMember)
            .options(joinedload(OrganizationMember.user))
            .filter(OrganizationMember.organization_id == organization_id)
        )
        if role is not None:
            query = query.filter(OrganizationMember.role == role)
        if is_active is not None:
            query = query.filter(OrganizationMember.is_active == is_active)

        total = query.count()
        members = query.order_by(OrganizationMember.joined_at.desc()).offset(skip).limit(limit).all()
        return members, total
