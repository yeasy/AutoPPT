"""
Custom exceptions for AutoPPT.

These exceptions provide user-friendly error messages and enable
structured error handling throughout the application.
"""

from __future__ import annotations


class AutoPPTError(Exception):
    """Base exception for all AutoPPT errors."""
    pass


class APIKeyError(AutoPPTError):
    """Raised when an API key is missing or invalid."""

    def __init__(self, provider: str, message: str | None = None):
        self.provider = provider
        self.message = message or f"API key for '{provider}' is missing or invalid. Please check your .env file."
        super().__init__(self.message)


class RateLimitError(AutoPPTError):
    """Raised when API rate limits are exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        self.provider = provider
        if retry_after is not None and retry_after < 0:
            retry_after = None
        self.retry_after = retry_after
        if retry_after is not None:
            self.message = f"Rate limit exceeded for '{provider}'. Please retry after {retry_after} seconds."
        else:
            self.message = f"Rate limit exceeded for '{provider}'. Please wait and try again later."
        super().__init__(self.message)


class RenderError(AutoPPTError):
    """Raised when PPT rendering operations fail."""

    def __init__(self, operation: str, reason: str | None = None):
        self.operation = operation
        self.reason = reason or "Unknown error"
        self.message = f"Failed to render '{operation}': {self.reason}"
        super().__init__(self.message)


