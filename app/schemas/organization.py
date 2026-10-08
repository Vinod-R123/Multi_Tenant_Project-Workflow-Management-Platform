from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import OrganizationRole
from app.schemas.auth import UserResponse


class OrganizationBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None
    role: OrganizationRole = OrganizationRole.TEAM_MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: OrganizationRole


class UpdateMemberStatusRequest(BaseModel):
    is_active: bool


class OrganizationMemberResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: OrganizationRole
    is_active: bool
    joined_at: datetime
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)
