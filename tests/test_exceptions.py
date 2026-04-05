import pytest

from autoppt.exceptions import (
    APIKeyError,
    AutoPPTError,
    RateLimitError,
    RenderError,
)


def test_api_key_error_message():
    exc = APIKeyError("openai")
    assert "openai" in str(exc)
    assert exc.provider == "openai"


def test_api_key_error_custom_message():
    exc = APIKeyError("google", message="custom msg")
    assert exc.message == "custom msg"


def test_rate_limit_error_with_retry():
    exc = RateLimitError("openai", retry_after=30)
    assert exc.retry_after == 30
    assert "30" in exc.message


def test_rate_limit_error_without_retry():
    exc = RateLimitError("openai")
    assert exc.retry_after is None
    assert "wait" in exc.message.lower()


def test_render_error():
    exc = RenderError("add_slide", reason="template missing")
    assert exc.operation == "add_slide"
    assert "template missing" in exc.message


def test_all_inherit_from_autoppt_error():
    assert issubclass(APIKeyError, AutoPPTError)
    assert issubclass(RateLimitError, AutoPPTError)
    assert issubclass(RenderError, AutoPPTError)


class TestRateLimitErrorNegativeRetryAfter:
    """Tests for RateLimitError with negative retry_after."""

    def test_negative_retry_after_becomes_none(self):
        """Negative retry_after should be normalized to None."""
        err = RateLimitError("openai", retry_after=-5)
        assert err.retry_after is None
        assert "-5" not in err.message

    def test_zero_retry_after_is_preserved(self):
        """Zero retry_after should be preserved."""
        err = RateLimitError("openai", retry_after=0)
        assert err.retry_after == 0

    def test_zero_retry_after_message_contains_retry_after_0(self):
        """Zero retry_after message should contain 'retry after 0'."""
        err = RateLimitError("openai", retry_after=0)
        assert "retry after 0" in err.message


def test_render_error_default_reason():
    """RenderError without reason should use 'Unknown error'."""
    exc = RenderError("add_slide")
    assert exc.reason == "Unknown error"
    assert "Unknown error" in exc.message
    assert "add_slide" in exc.message


def test_exceptions_can_be_raised_and_caught_as_base():
    """All custom exceptions should be catchable as AutoPPTError."""
    with pytest.raises(AutoPPTError):
        raise APIKeyError("openai")

    with pytest.raises(AutoPPTError):
        raise RateLimitError("openai", retry_after=30)

    with pytest.raises(AutoPPTError):
        raise RenderError("save", reason="disk full")


def test_api_key_error_default_message_format():
    """APIKeyError default message should follow expected template."""
    exc = APIKeyError("anthropic")
    assert exc.message == "API key for 'anthropic' is missing or invalid. Please check your .env file."
