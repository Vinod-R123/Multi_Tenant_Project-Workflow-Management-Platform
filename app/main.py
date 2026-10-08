import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api_router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.db.session import engine
from app.models import Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up Multi-Tenant Platform Backend...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown actions
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-Tenant Project & Workflow Management Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standardized Exception Handling
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Sanitize pydantic validation errors for serialization
    cleaned_errors = []
    for err in exc.errors():
        err_dict = dict(err)
        if "input" in err_dict and not isinstance(err_dict["input"], (str, int, float, bool, list, dict, type(None))):
            err_dict["input"] = str(err_dict["input"])
        cleaned_errors.append(err_dict)

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload or parameters",
                "details": cleaned_errors,
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact support.",
                "details": str(exc) if os.getenv("DEBUG") == "True" else None,
            }
        }
    )


# Include API routes under /api/v1 as well as /api for compatibility
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": settings.VERSION}
