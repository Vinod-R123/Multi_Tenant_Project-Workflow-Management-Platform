from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_organization_context
from app.core.response import APIResponse
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=APIResponse[DashboardResponse])
def get_dashboard_stats(
    org_id: int = Depends(get_organization_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = DashboardService(db)
    metrics = service.get_dashboard_metrics(org_id, current_user)
    return APIResponse(success=True, data=metrics)
