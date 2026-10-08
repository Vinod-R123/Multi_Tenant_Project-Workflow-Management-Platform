from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import OrganizationRole


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: Optional[str] = None


class RegisterRequest(UserBase):
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_super_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MembershipSummary(BaseModel):
    organization_id: int
    organization_name: str
    organization_slug: str
    role: OrganizationRole
    is_active: bool


class UserProfileResponse(UserResponse):
    organizations: List[MembershipSummary] = []


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
