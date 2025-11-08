"""Custom exceptions."""

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize exception."""
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        """Initialize not found error."""
        super().__init__(message, status_code=404, details=details)


class ValidationError(AppException):
    """Validation error exception."""

    def __init__(self, message: str = "Validation error", details: dict[str, Any] | None = None):
        """Initialize validation error."""
        super().__init__(message, status_code=422, details=details)


class DatabaseError(AppException):
    """Database error exception."""

    def __init__(self, message: str = "Database error", details: dict[str, Any] | None = None):
        """Initialize database error."""
        super().__init__(message, status_code=500, details=details)
