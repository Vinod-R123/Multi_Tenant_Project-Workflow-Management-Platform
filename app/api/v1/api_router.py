from fastapi import APIRouter
from app.api.v1.endpoints import (
    audit_logs,
    auth,
    comments,
    dashboard,
    files,
    notifications,
    organizations,
    projects,
    tasks,
    websockets,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(comments.router)
api_router.include_router(files.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit_logs.router)
api_router.include_router(websockets.router)
