from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMetadata(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMetadata


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: PaginatedData[T]
