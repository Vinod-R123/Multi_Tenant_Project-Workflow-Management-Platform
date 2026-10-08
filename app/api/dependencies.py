from typing import List, Optional
from fastapi import Depends, Header, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.exceptions import AuthenticationError, ForbiddenError, BadRequestError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import OrganizationRole
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise AuthenticationError(message="Not authenticated", code="UNAUTHENTICATED")

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type", code="INVALID_TOKEN_TYPE")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError(message="Invalid token subject", code="TOKEN_INVALID")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise AuthenticationError(message="Invalid user ID in token", code="TOKEN_INVALID")

    user_repo = UserRepository(db)
    user = user_repo.get(user_id)
    if not user:
        raise AuthenticationError(message="User not found", code="USER_NOT_FOUND")

    if not user.is_active:
        raise AuthenticationError(message="User account is inactive", code="USER_INACTIVE")

    return user


def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_super_admin:
        raise ForbiddenError(message="Super Admin access required", code="SUPER_ADMIN_REQUIRED")
    return current_user


def get_organization_context(
    x_organization_id: Optional[int] = Header(None, alias="X-Organization-ID"),
    org_id_query: Optional[int] = Query(None, alias="org_id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> int:
    """
    Resolves and verifies active organization context for the request.
    Precedence:
    1. Header `X-Organization-ID`
    2. Query param `org_id`
    3. User's primary/first active organization membership
    """
    resolved_org_id = x_organization_id or org_id_query
    org_repo = OrganizationRepository(db)

    if resolved_org_id is None:
        # Fallback to user's first organization
        user_memberships = org_repo.list_user_organizations(current_user.id)
        if not user_memberships:
            raise BadRequestError(
                message="Organization context required. Pass X-Organization-ID header or create/join an organization.",
                code="ORGANIZATION_CONTEXT_REQUIRED"
            )
        resolved_org_id = user_memberships[0][0].id

    # Verify user belongs to this organization
    if not current_user.is_super_admin:
        member = org_repo.get_member(resolved_org_id, current_user.id)
        if not member or not member.is_active:
            raise ForbiddenError(
                message="You do not have access to this organization",
                code="ORGANIZATION_ACCESS_DENIED"
            )

    return resolved_org_id


class RoleChecker:
    def __init__(self, allowed_roles: List[OrganizationRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        org_id: int = Depends(get_organization_context),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> OrganizationMember:
        if current_user.is_super_admin:
            return OrganizationMember(
                organization_id=org_id,
                user_id=current_user.id,
                role=OrganizationRole.ORGANIZATION_ADMIN,
                is_active=True,
            )

        org_repo = OrganizationRepository(db)
        member = org_repo.get_member(org_id, current_user.id)
        if not member or not member.is_active:
            raise ForbiddenError(
                message="You do not have access to this organization",
                code="ORGANIZATION_ACCESS_DENIED"
            )

        if member.role not in self.allowed_roles:
            raise ForbiddenError(
                message=f"Action requires one of roles: {[r.value for r in self.allowed_roles]}",
                code="INSUFFICIENT_PERMISSIONS"
            )
        return member


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
