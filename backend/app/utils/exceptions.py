"""
IntelliDesk AI — Custom Exceptions
Structured exception hierarchy for consistent error handling.
"""


class IntelliDeskError(Exception):
    """Base exception for all IntelliDesk AI application errors."""

    def __init__(self, message: str = "An error occurred."):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class ValidationError(IntelliDeskError):
    """Raised when input validation fails (HTTP 400)."""

    def __init__(self, message: str = "Validation failed.", details: list | None = None):
        super().__init__(message)
        self.details = details or []


class NotFoundError(IntelliDeskError):
    """Raised when a requested resource does not exist (HTTP 404)."""

    def __init__(self, resource: str = "Resource", identifier: str | int | None = None):
        if identifier:
            message = f"{resource} with id '{identifier}' was not found."
        else:
            message = f"{resource} was not found."
        super().__init__(message)


class AuthorizationError(IntelliDeskError):
    """Raised when a user lacks permission for an action (HTTP 403)."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(message)


class AuthenticationError(IntelliDeskError):
    """Raised when authentication fails (HTTP 401)."""

    def __init__(self, message: str = "Authentication failed."):
        super().__init__(message)


class ConflictError(IntelliDeskError):
    """Raised when a resource conflict occurs (HTTP 409), e.g., duplicate email."""

    def __init__(self, message: str = "A conflict occurred with an existing resource."):
        super().__init__(message)


class BusinessLogicError(IntelliDeskError):
    """Raised when a business rule is violated (HTTP 422)."""

    def __init__(self, message: str = "The request violates business logic rules."):
        super().__init__(message)


class AIServiceError(IntelliDeskError):
    """Raised when the AI provider is unavailable or returns an error (HTTP 503)."""

    def __init__(self, message: str = "AI service is temporarily unavailable."):
        super().__init__(message)


class StorageError(IntelliDeskError):
    """Raised when file storage operations fail."""

    def __init__(self, message: str = "File storage operation failed."):
        super().__init__(message)
