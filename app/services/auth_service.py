from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import AuditAction
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MembershipSummary,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserResponse,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def register(self, req: RegisterRequest) -> UserResponse:
        # Check existing email
        if self.user_repo.get_by_email(req.email):
            raise ConflictError(message="Email is already registered", code="EMAIL_ALREADY_EXISTS")

        # Check existing username
        if self.user_repo.get_by_username(req.username):
            raise ConflictError(message="Username is already taken", code="USERNAME_ALREADY_EXISTS")

        user = User(
            email=req.email.lower(),
            username=req.username,
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            is_active=True,
            is_super_admin=False,
        )
        created_user = self.user_repo.create(user)
        return UserResponse.model_validate(created_user)

    def login(self, req: LoginRequest, ip_address: Optional[str] = None) -> TokenResponse:
        user = self.user_repo.get_by_username_or_email(req.username_or_email)
        if not user:
            raise AuthenticationError(message="Invalid credentials", code="INVALID_CREDENTIALS")

        if not user.is_active:
            raise AuthenticationError(message="User account is deactivated", code="USER_INACTIVE")

        if not verify_password(req.password, user.hashed_password):
            raise AuthenticationError(message="Invalid credentials", code="INVALID_CREDENTIALS")

        # Create access token and refresh token
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "username": user.username, "is_super_admin": user.is_super_admin}
        )
        refresh_token_str, jti, expire = create_refresh_token(subject=str(user.id))
        self.user_repo.store_refresh_token(user_id=user.id, jti=jti, expires_at=expire)

        # Audit log login
        memberships = self.org_repo.list_user_organizations(user.id)
        if memberships:
            first_org = memberships[0][0]
            self.audit_repo.log(
                organization_id=first_org.id,
                action=AuditAction.LOGIN.value,
                entity_type="User",
                entity_id=user.id,
                user_id=user.id,
                ip_address=ip_address,
                details={"username": user.username}
            )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthenticationError(message="Invalid token type", code="TOKEN_INVALID")

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            raise AuthenticationError(message="Invalid token payload", code="TOKEN_INVALID")

        token_record = self.user_repo.get_valid_refresh_token(jti)
        if not token_record:
            raise AuthenticationError(message="Refresh token has been revoked or expired", code="TOKEN_REVOKED")

        # Rotate token: revoke old token
        self.user_repo.revoke_refresh_token(jti)

        user = self.user_repo.get(int(user_id))
        if not user or not user.is_active:
            raise AuthenticationError(message="User inactive or not found", code="USER_INACTIVE")

        # Create new pair
        new_access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email, "username": user.username, "is_super_admin": user.is_super_admin}
        )
        new_refresh_token_str, new_jti, new_expire = create_refresh_token(subject=str(user.id))
        self.user_repo.store_refresh_token(user_id=user.id, jti=new_jti, expires_at=new_expire)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    def logout(self, refresh_token_str: str, user_id: int) -> bool:
        try:
            payload = decode_token(refresh_token_str)
            jti = payload.get("jti")
            if jti:
                self.user_repo.revoke_refresh_token(jti)
        except Exception:
            pass
        return True

    def change_password(self, user: User, req: ChangePasswordRequest, ip_address: Optional[str] = None) -> bool:
        if not verify_password(req.current_password, user.hashed_password):
            raise AuthenticationError(message="Incorrect current password", code="INVALID_CURRENT_PASSWORD")

        user.hashed_password = hash_password(req.new_password)
        self.user_repo.update(user)
        # Revoke existing refresh tokens for security
        self.user_repo.revoke_all_user_tokens(user.id)
        return True

    def get_profile(self, user: User) -> UserProfileResponse:
        memberships = self.org_repo.list_user_organizations(user.id)
        org_summaries = [
            MembershipSummary(
                organization_id=org.id,
                organization_name=org.name,
                organization_slug=org.slug,
                role=member.role,
                is_active=member.is_active,
            )
            for org, member in memberships
        ]
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_super_admin=user.is_super_admin,
            created_at=user.created_at,
            organizations=org_summaries,
        )
