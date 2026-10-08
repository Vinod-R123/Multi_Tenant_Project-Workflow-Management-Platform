from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid authentication credentials", code: str = "AUTHENTICATION_FAILED", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=401, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to access this resource", code: str = "FORBIDDEN", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=403, details=details)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "RESOURCE_NOT_FOUND", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=404, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict detected", code: str = "CONFLICT", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=409, details=details)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", code: str = "BAD_REQUEST", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=400, details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=422, details=details)
