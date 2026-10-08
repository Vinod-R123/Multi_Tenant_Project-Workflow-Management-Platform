import re
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.enums import AuditAction, OrganizationRole
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.organization import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def create_organization(self, user: User, req: OrganizationCreate, ip_address: Optional[str] = None) -> OrganizationResponse:
        slug = req.slug or slugify(req.name)
        if self.org_repo.get_by_slug(slug):
            # If slug exists, append random suffix or check error
            slug = f"{slug}-{user.id}"

        if self.org_repo.get_by_slug(slug):
            raise ConflictError(message="Organization slug already exists", code="SLUG_ALREADY_EXISTS")

        org = Organization(
            name=req.name,
            slug=slug,
            description=req.description,
            is_active=True,
        )
        created_org = self.org_repo.create(org)

        # Creator is assigned ORGANIZATION_ADMIN
        self.org_repo.add_member(
            organization_id=created_org.id,
            user_id=user.id,
            role=OrganizationRole.ORGANIZATION_ADMIN,
            is_active=True,
        )

        self.audit_repo.log(
            organization_id=created_org.id,
            action=AuditAction.ORG_CREATED.value,
            entity_type="Organization",
            entity_id=created_org.id,
            user_id=user.id,
            ip_address=ip_address,
            details={"name": created_org.name, "slug": created_org.slug}
        )

        return OrganizationResponse.model_validate(created_org)

    def get_organization(self, org_id: int, user: User) -> OrganizationResponse:
        self.verify_membership(org_id, user)
        org = self.org_repo.get(org_id)
        if not org or not org.is_active:
            raise NotFoundError(message="Organization not found", code="ORGANIZATION_NOT_FOUND")
        return OrganizationResponse.model_validate(org)

    def list_user_organizations(self, user: User) -> List[OrganizationResponse]:
        memberships = self.org_repo.list_user_organizations(user.id)
        return [OrganizationResponse.model_validate(org) for org, _ in memberships]

    def update_organization(
        self,
        org_id: int,
        req: OrganizationUpdate,
        user: User,
        ip_address: Optional[str] = None
    ) -> OrganizationResponse:
        self.verify_role(org_id, user, [OrganizationRole.ORGANIZATION_ADMIN])
        org = self.org_repo.get(org_id)
        if not org:
            raise NotFoundError(message="Organization not found", code="ORGANIZATION_NOT_FOUND")

        if req.name is not None:
            org.name = req.name
        if req.description is not None:
            org.description = req.description
        if req.is_active is not None:
            org.is_active = req.is_active

        updated_org = self.org_repo.update(org)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.ORG_UPDATED.value,
            entity_type="Organization",
            entity_id=org_id,
            user_id=user.id,
            ip_address=ip_address,
            details=req.model_dump(exclude_unset=True)
        )

        return OrganizationResponse.model_validate(updated_org)

    def add_member(
        self,
        org_id: int,
        req: AddMemberRequest,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> OrganizationMemberResponse:
        self.verify_role(org_id, actor_user, [OrganizationRole.ORGANIZATION_ADMIN])
        
        target_user: Optional[User] = None
        if req.user_id:
            target_user = self.user_repo.get(req.user_id)
        elif req.email:
            target_user = self.user_repo.get_by_email(req.email)
        elif req.username:
            target_user = self.user_repo.get_by_username(req.username)

        if not target_user:
            raise NotFoundError(message="User not found", code="USER_NOT_FOUND")

        if not target_user.is_active:
            raise BadRequestError(message="Cannot add inactive user to organization", code="USER_INACTIVE")

        # Check existing membership
        existing = self.org_repo.get_member(org_id, target_user.id)
        if existing:
            raise ConflictError(message="User is already a member of this organization", code="DUPLICATE_MEMBERSHIP")

        member = self.org_repo.add_member(
            organization_id=org_id,
            user_id=target_user.id,
            role=req.role,
            is_active=True,
        )

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.MEMBER_ADDED.value,
            entity_type="OrganizationMember",
            entity_id=member.id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"target_user_id": target_user.id, "role": req.role.value}
        )

        return OrganizationMemberResponse.model_validate(member)

    def remove_member(
        self,
        org_id: int,
        target_user_id: int,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> bool:
        self.verify_role(org_id, actor_user, [OrganizationRole.ORGANIZATION_ADMIN])

        member = self.org_repo.get_member(org_id, target_user_id)
        if not member:
            raise NotFoundError(message="Member not found in organization", code="MEMBER_NOT_FOUND")

        if target_user_id == actor_user.id:
            raise BadRequestError(message="Cannot remove yourself from organization", code="SELF_REMOVAL_FORBIDDEN")

        self.org_repo.remove_member(org_id, target_user_id)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.MEMBER_REMOVED.value,
            entity_type="OrganizationMember",
            entity_id=member.id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"removed_user_id": target_user_id}
        )
        return True

    def update_member_role(
        self,
        org_id: int,
        target_user_id: int,
        new_role: OrganizationRole,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> OrganizationMemberResponse:
        self.verify_role(org_id, actor_user, [OrganizationRole.ORGANIZATION_ADMIN])

        member = self.org_repo.get_member(org_id, target_user_id)
        if not member:
            raise NotFoundError(message="Member not found", code="MEMBER_NOT_FOUND")

        old_role = member.role
        member.role = new_role
        updated_member = self.db.merge(member)
        self.db.commit()
        self.db.refresh(updated_member)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.MEMBER_ROLE_CHANGED.value,
            entity_type="OrganizationMember",
            entity_id=updated_member.id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"target_user_id": target_user_id, "old_role": old_role.value, "new_role": new_role.value}
        )

        return OrganizationMemberResponse.model_validate(updated_member)

    def update_member_status(
        self,
        org_id: int,
        target_user_id: int,
        is_active: bool,
        actor_user: User,
        ip_address: Optional[str] = None
    ) -> OrganizationMemberResponse:
        self.verify_role(org_id, actor_user, [OrganizationRole.ORGANIZATION_ADMIN])

        member = self.org_repo.get_member(org_id, target_user_id)
        if not member:
            raise NotFoundError(message="Member not found", code="MEMBER_NOT_FOUND")

        member.is_active = is_active
        updated_member = self.db.merge(member)
        self.db.commit()
        self.db.refresh(updated_member)

        self.audit_repo.log(
            organization_id=org_id,
            action=AuditAction.MEMBER_STATUS_CHANGED.value,
            entity_type="OrganizationMember",
            entity_id=updated_member.id,
            user_id=actor_user.id,
            ip_address=ip_address,
            details={"target_user_id": target_user_id, "is_active": is_active}
        )

        return OrganizationMemberResponse.model_validate(updated_member)

    def list_members(
        self,
        org_id: int,
        user: User,
        skip: int = 0,
        limit: int = 20,
        role: Optional[OrganizationRole] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[OrganizationMemberResponse], int]:
        self.verify_membership(org_id, user)
        members, total = self.org_repo.list_members(
            organization_id=org_id,
            skip=skip,
            limit=limit,
            role=role,
            is_active=is_active,
        )
        return [OrganizationMemberResponse.model_validate(m) for m in members], total

    def verify_membership(self, org_id: int, user: User) -> OrganizationMember:
        if user.is_super_admin:
            # Super admins have full access across all organizations
            member = self.org_repo.get_member(org_id, user.id)
            if not member:
                # Provide a synthetic or first admin membership context
                return OrganizationMember(
                    organization_id=org_id,
                    user_id=user.id,
                    role=OrganizationRole.ORGANIZATION_ADMIN,
                    is_active=True,
                )
            return member

        member = self.org_repo.get_member(org_id, user.id)
        if not member or not member.is_active:
            raise ForbiddenError(
                message="You do not have access to this organization",
                code="ORGANIZATION_ACCESS_DENIED"
            )
        return member

    def verify_role(self, org_id: int, user: User, allowed_roles: List[OrganizationRole]) -> OrganizationMember:
        member = self.verify_membership(org_id, user)
        if user.is_super_admin:
            return member

        if member.role not in allowed_roles:
            raise ForbiddenError(
                message=f"Action requires one of roles: {[r.value for r in allowed_roles]}",
                code="INSUFFICIENT_PERMISSIONS"
            )
        return member
