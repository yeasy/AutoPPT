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
