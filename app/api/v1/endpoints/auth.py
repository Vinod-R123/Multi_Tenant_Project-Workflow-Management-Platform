from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.api.dependencies import get_client_ip, get_current_user
from app.core.response import APIResponse
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[UserResponse], status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    user_resp = service.register(req)
    return APIResponse(success=True, data=user_resp)


@router.post("/login", response_model=APIResponse[TokenResponse])
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    ip_addr = get_client_ip(request)
    token_resp = service.login(req, ip_address=ip_addr)
    return APIResponse(success=True, data=token_resp)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    token_resp = service.refresh_token(req.refresh_token)
    return APIResponse(success=True, data=token_resp)


@router.post("/logout", response_model=APIResponse[dict])
def logout(
    req: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    service.logout(req.refresh_token, current_user.id)
    return APIResponse(success=True, data={"message": "Logged out successfully"})


@router.get("/me", response_model=APIResponse[UserProfileResponse])
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    profile = service.get_profile(current_user)
    return APIResponse(success=True, data=profile)


@router.post("/change-password", response_model=APIResponse[dict])
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    ip_addr = get_client_ip(request)
    service.change_password(current_user, req, ip_address=ip_addr)
    return APIResponse(success=True, data={"message": "Password changed successfully"})
