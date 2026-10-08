from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Tenant Project & Workflow Management Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres@localhost:5433/multitenant_pm",
        description="Database connection URL"
    )

    # Security & JWT
    SECRET_KEY: str = Field(
        default="super-secret-system-key-change-in-production-1234567890",
        description="Secret key for JWT generation"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # File Upload Configuration
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg", "gif", "txt", "zip"
    ]
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "image/png",
        "image/jpeg",
        "image/gif",
        "text/plain",
        "application/zip",
        "application/x-zip-compressed"
    ]

    # WebSocket
    WS_HEARTBEAT_INTERVAL_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
