"""
Custom exceptions for AutoPPT.

These exceptions provide user-friendly error messages and enable
structured error handling throughout the application.
"""


class AutoPPTError(Exception):
    """Base exception for all AutoPPT errors."""
    pass


class APIKeyError(AutoPPTError):
    """Raised when an API key is missing or invalid."""
    
    def __init__(self, provider: str, message: str = None):
        self.provider = provider
        self.message = message or f"API key for '{provider}' is missing or invalid. Please check your .env file."
        super().__init__(self.message)


class RateLimitError(AutoPPTError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        if retry_after:
            self.message = f"Rate limit exceeded for '{provider}'. Please retry after {retry_after} seconds."
        else:
            self.message = f"Rate limit exceeded for '{provider}'. Please wait and try again later."
        super().__init__(self.message)


class ResearchError(AutoPPTError):
    """Raised when research/web search operations fail."""
    
    def __init__(self, query: str, reason: str = None):
        self.query = query
        self.reason = reason or "Unknown error"
        self.message = f"Failed to research '{query}': {self.reason}"
        super().__init__(self.message)


class RenderError(AutoPPTError):
    """Raised when PPT rendering operations fail."""
    
    def __init__(self, operation: str, reason: str = None):
        self.operation = operation
        self.reason = reason or "Unknown error"
        self.message = f"Failed to render '{operation}': {self.reason}"
        super().__init__(self.message)


class ModelNotFoundError(AutoPPTError):
    """Raised when the specified LLM model is not available."""
    
    def __init__(self, model: str, provider: str):
        self.model = model
        self.provider = provider
        self.message = f"Model '{model}' is not available for provider '{provider}'."
        super().__init__(self.message)
