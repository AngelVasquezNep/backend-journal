"""Owned safe failures distinguish authentication, policy, validation and dependency errors."""


class ApplicationError(Exception):
    """Expose only a stable safe code, message and public HTTP status to adapters."""

    def __init__(self, code: str, message: str, status: int = 422) -> None:
        """Store safe corrective information; never accept private provider/parser diagnostics."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class DependencyUnavailable(ApplicationError):
    """A required service failed; this is never evidence that company knowledge is absent."""

    def __init__(self) -> None:
        """Create a redacted retryable failure without the underlying dependency payload."""
        super().__init__(
            "dependency_unavailable", "A required service is temporarily unavailable.", 503
        )


class AuthenticationRequired(ApplicationError):
    """A missing, revoked, expired or invalid session grants no authority."""

    def __init__(self) -> None:
        """Create an indistinguishable authentication denial."""
        super().__init__("authentication_required", "Please log in again.", 401)


class ValidationFailed(ApplicationError, ValueError):
    """A safe Identity input failure also retains the value-object ValueError contract."""

    def __init__(self, message: str) -> None:
        """Expose only an application-owned corrective message and the documented 422 status."""
        super().__init__("validation_failed", message, 422)
