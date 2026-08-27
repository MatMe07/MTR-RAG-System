from typing import Any


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        http_status: int = 500,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Not found", details: dict | None = None):
        super().__init__(code="NOT_FOUND", message=message, details=details, http_status=404)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation error", details: dict | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, details=details, http_status=422)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", details: dict | None = None):
        super().__init__(code="UNAUTHORIZED", message=message, details=details, http_status=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", details: dict | None = None):
        super().__init__(code="FORBIDDEN", message=message, details=details, http_status=403)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict", details: dict | None = None):
        super().__init__(code="CONFLICT", message=message, details=details, http_status=409)


class InternalError(AppException):
    def __init__(self, message: str = "Internal error", details: dict | None = None):
        super().__init__(code="INTERNAL_ERROR", message=message, details=details, http_status=500)
