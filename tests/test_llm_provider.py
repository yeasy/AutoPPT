"""
Unit tests for LLM providers.
"""
import pytest
from typing import List

from autoppt.llm_provider import (
    BaseLLMProvider,
    MockProvider,
    OpenAIProvider,
    get_provider
)
from autoppt.data_types import (
    PresentationOutline,
    PresentationSection,
    SlideConfig
)


class TestMockProvider:
    """Tests for MockProvider class."""

    def test_mock_provider_instantiation(self):
        """Test that MockProvider can be instantiated."""
        provider = MockProvider()
        assert provider is not None
        assert isinstance(provider, BaseLLMProvider)

    def test_generate_text(self):
        """Test generate_text returns a string."""
        provider = MockProvider()
        result = provider.generate_text("Test prompt")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "content" in result.lower() or "presentation" in result.lower()

    def test_generate_structure_outline(self):
        """Test generate_structure returns valid PresentationOutline."""
        provider = MockProvider()
        prompt = "Create outline for topic: Quantum Computing"

        result = provider.generate_structure(prompt, PresentationOutline)

        assert isinstance(result, PresentationOutline)
        assert isinstance(result.title, str)
        assert len(result.title) > 0
        assert isinstance(result.sections, list)
        assert len(result.sections) > 0

        for section in result.sections:
            assert isinstance(section, PresentationSection)
            assert isinstance(section.title, str)
            assert isinstance(section.slides, list)

    def test_generate_structure_slide_config(self):
        """Test generate_structure returns valid SlideConfig."""
        provider = MockProvider()
        prompt = "Create slide about Machine Learning"

        result = provider.generate_structure(prompt, SlideConfig)

        assert isinstance(result, SlideConfig)
        assert isinstance(result.title, str)
        assert isinstance(result.bullets, list)
        assert len(result.bullets) > 0


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_get_mock_provider(self):
        """Test getting mock provider."""
        provider = get_provider("mock")
        assert isinstance(provider, MockProvider)

    def test_get_provider_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        provider1 = get_provider("Mock")
        provider2 = get_provider("MOCK")
        provider3 = get_provider("mock")

        assert isinstance(provider1, MockProvider)
        assert isinstance(provider2, MockProvider)
        assert isinstance(provider3, MockProvider)

    def test_get_unknown_provider_raises(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("unknown_provider")

        assert "Unknown provider" in str(exc_info.value)
        assert "unknown_provider" in str(exc_info.value)


class TestRetryLogic:
    """Tests for _run_with_retries."""

    def test_retries_on_rate_limit(self):
        from autoppt.llm_provider import _run_with_retries, _is_rate_limit_error
        from autoppt.exceptions import RateLimitError
        from unittest.mock import patch

        call_count = 0

        def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 rate limit exceeded")
            return "success"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 0
            result = _run_with_retries("test", flaky_op)

        assert result == "success"
        assert call_count == 2

    def test_raises_non_rate_limit_error_immediately(self):
        from autoppt.llm_provider import _run_with_retries
        from unittest.mock import patch

        def bad_op():
            raise TypeError("something wrong")

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 0
            with pytest.raises(TypeError, match="something wrong"):
                _run_with_retries("test", bad_op)

    def test_rate_limit_detection(self):
        from autoppt.llm_provider import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("Error 429: rate limit")) is True
        assert _is_rate_limit_error(Exception("quota exceeded")) is True
        assert _is_rate_limit_error(Exception("something else")) is False

    def test_rate_limit_detection_from_status_code_attr(self):
        from autoppt.llm_provider import _is_rate_limit_error

        class HTTPError(Exception):
            status_code = 429

        assert _is_rate_limit_error(HTTPError("too many requests")) is True

    def test_rate_limit_detection_from_status_attr(self):
        from autoppt.llm_provider import _is_rate_limit_error

        class APIError(Exception):
            status = 429

        assert _is_rate_limit_error(APIError("rate limited")) is True


class TestIsTransientError:
    """Tests for _is_transient_error detection."""

    def test_status_code_500_is_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 500

        assert _is_transient_error(HTTPError("internal server error")) is True

    def test_status_code_502_is_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 502

        assert _is_transient_error(HTTPError("bad gateway")) is True

    def test_status_code_503_is_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 503

        assert _is_transient_error(HTTPError("service unavailable")) is True

    def test_status_code_529_is_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 529

        assert _is_transient_error(HTTPError("overloaded")) is True

    def test_status_code_400_is_not_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 400

        assert _is_transient_error(HTTPError("bad request")) is False

    def test_status_code_404_is_not_transient(self):
        from autoppt.llm_provider import _is_transient_error

        class HTTPError(Exception):
            status_code = 404

        assert _is_transient_error(HTTPError("not found")) is False

    def test_connection_reset_message_is_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("connection reset by peer")) is True

    def test_timeout_message_is_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("request timeout")) is True

    def test_overloaded_message_is_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("server is overloaded")) is True

    def test_bad_gateway_message_is_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("502 bad gateway")) is True

    def test_unrelated_message_is_not_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("invalid JSON")) is False

    def test_unrelated_message_no_status_is_not_transient(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("missing required field")) is False

    def test_status_attr_also_detected(self):
        """_is_transient_error checks 'status' attr as well as 'status_code'."""
        from autoppt.llm_provider import _is_transient_error

        class APIError(Exception):
            status = 503

        assert _is_transient_error(APIError("unavailable")) is True


class TestTransientRetryPath:
    """Tests for transient-error retry behaviour in _run_with_retries."""

    def test_transient_error_is_retried(self):
        """A transient 503 should be retried and succeed on later attempt."""
        from autoppt.llm_provider import _run_with_retries
        from unittest.mock import patch

        call_count = 0

        class TransientError(Exception):
            status_code = 503

        def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("service unavailable")
            return "ok"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 0
            mock_config.TRANSIENT_RETRY_BASE_SECONDS = 0
            result = _run_with_retries("test", flaky_op)

        assert result == "ok"
        assert call_count == 2

    def test_transient_exhaustion_reraises_original_error(self):
        """After all retries exhausted on transient errors, the original error
        should be re-raised -- NOT wrapped in RateLimitError."""
        from autoppt.llm_provider import _run_with_retries
        from autoppt.exceptions import RateLimitError
        from unittest.mock import patch

        class TransientError(Exception):
            status_code = 503

        def always_fail():
            raise TransientError("service unavailable")

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 0
            mock_config.TRANSIENT_RETRY_BASE_SECONDS = 0
            with pytest.raises(TransientError, match="service unavailable"):
                _run_with_retries("test", always_fail)


class TestCodeFenceStripping:
    """Tests for Anthropic code fence extraction via the real provider path."""

    def test_strips_json_fence(self):
        """Ensure ```json fenced responses are parsed correctly."""
        from unittest.mock import MagicMock, patch
        from autoppt.data_types import SlideConfig

        fake_content = MagicMock()
        fake_content.text = '```json\n{"title":"Test","bullets":["A"],"slide_type":"content","citations":[]}\n```'
        fake_message = MagicMock()
        fake_message.content = [fake_content]

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_config.ANTHROPIC_API_KEY = "test-key"
            mock_config.DEFAULT_ANTHROPIC_MODEL = "claude-test"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            client = mock_anthropic_cls.return_value
            client.messages.create.return_value = fake_message

            from autoppt.llm_provider import AnthropicProvider
            provider = AnthropicProvider.__new__(AnthropicProvider)
            provider.client = client
            provider.model = "claude-test"

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Test"

    def test_strips_generic_fence_with_language_tag(self):
        """Ensure ```python fenced responses strip the language tag."""
        from unittest.mock import MagicMock, patch
        from autoppt.data_types import SlideConfig

        fake_content = MagicMock()
        fake_content.text = '```python\n{"title":"Test","bullets":["B"],"slide_type":"content","citations":[]}\n```'
        fake_message = MagicMock()
        fake_message.content = [fake_content]

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_config.ANTHROPIC_API_KEY = "test-key"
            mock_config.DEFAULT_ANTHROPIC_MODEL = "claude-test"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            client = mock_anthropic_cls.return_value
            client.messages.create.return_value = fake_message

            from autoppt.llm_provider import AnthropicProvider
            provider = AnthropicProvider.__new__(AnthropicProvider)
            provider.client = client
            provider.model = "claude-test"

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Test"


class TestIsLocalBaseUrl:
    """Tests for _is_local_base_url hostname parsing."""

    def test_localhost_is_local(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://localhost:8080/v1") is True

    def test_loopback_is_local(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://127.0.0.1:11434") is True

    def test_evil_subdomain_not_local(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("https://not-127.0.0.1.evil.com") is False

    def test_evil_path_not_local(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("https://evil.com/localhost/proxy") is False

    def test_none_is_not_local(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url(None) is False


class TestProviderInterface:
    """Tests for BaseLLMProvider interface compliance."""

    def test_mock_provider_has_required_methods(self):
        """Test MockProvider has all required methods."""
        provider = MockProvider()

        assert hasattr(provider, 'generate_text')
        assert hasattr(provider, 'generate_structure')
        assert callable(provider.generate_text)
        assert callable(provider.generate_structure)


class TestOpenAIProviderConstructor:
    """Tests for OpenAIProvider constructor edge cases."""

    def test_local_base_url_no_api_key_allowed(self):
        """Local base_url should not require an API key."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = None
            mock_openai_cls.return_value = MagicMock()

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider(base_url="http://localhost:8080")
            assert provider.model == "gpt-5.4-mini"
            # Should have appended /v1 since it's a local URL without v1
            mock_openai_cls.assert_called_once()
            call_kwargs = mock_openai_cls.call_args[1]
            assert call_kwargs["base_url"] == "http://localhost:8080/v1"
            assert call_kwargs["api_key"] == "local-dev"

    def test_local_base_url_with_v1_not_duplicated(self):
        """Local base_url already containing v1 should not get /v1 appended."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = None
            mock_openai_cls.return_value = MagicMock()

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider(base_url="http://localhost:8080/v1")
            call_kwargs = mock_openai_cls.call_args[1]
            assert call_kwargs["base_url"] == "http://localhost:8080/v1"

    def test_remote_url_no_api_key_raises(self):
        """Remote base_url without API key should raise APIKeyError."""
        from unittest.mock import patch, MagicMock
        from autoppt.exceptions import APIKeyError

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = None

            from autoppt.llm_provider import OpenAIProvider
            with pytest.raises(APIKeyError):
                OpenAIProvider(base_url="https://api.openai.com/v1")

    def test_no_base_url_no_api_key_raises(self):
        """No base_url and no API key should raise APIKeyError."""
        from unittest.mock import patch, MagicMock
        from autoppt.exceptions import APIKeyError
        import os

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch.dict(os.environ, {}, clear=False):
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = None
            # Ensure OPENAI_API_BASE is not set
            os.environ.pop("OPENAI_API_BASE", None)

            from autoppt.llm_provider import OpenAIProvider
            with pytest.raises(APIKeyError):
                OpenAIProvider()

    def test_env_base_url_used_when_no_explicit_base(self):
        """OPENAI_API_BASE env var should be used as fallback."""
        from unittest.mock import patch, MagicMock
        import os

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls, \
             patch.dict(os.environ, {"OPENAI_API_BASE": "http://127.0.0.1:5000"}, clear=False):
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = None
            mock_openai_cls.return_value = MagicMock()

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            call_kwargs = mock_openai_cls.call_args[1]
            assert "127.0.0.1" in call_kwargs["base_url"]

    def test_custom_model(self):
        """Custom model parameter should be stored."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value = MagicMock()

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider(model="gpt-4-turbo")
            assert provider.model == "gpt-4-turbo"


class TestOpenAIProviderGenerate:
    """Tests for OpenAIProvider generate methods with null responses."""

    def test_generate_text_null_content_raises(self):
        """generate_text should raise ValueError when content is None."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_choice = MagicMock()
            mock_choice.message.content = None
            mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            with pytest.raises(ValueError, match="no content"):
                provider.generate_text("test prompt")

    def test_generate_structure_null_parsed_raises(self):
        """generate_structure should raise ValueError when parsed is None."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_choice = MagicMock()
            mock_choice.message.parsed = None
            mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            with pytest.raises(ValueError, match="returned None"):
                provider.generate_structure("test", SlideConfig)


class TestGoogleProviderConstructor:
    """Tests for GoogleProvider constructor."""

    def test_no_api_key_raises(self):
        """GoogleProvider should raise APIKeyError when no key provided."""
        from unittest.mock import patch, MagicMock
        from autoppt.exceptions import APIKeyError

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = None

            from autoppt.llm_provider import GoogleProvider
            with pytest.raises(APIKeyError):
                GoogleProvider()

    def test_explicit_api_key(self):
        """GoogleProvider should accept an explicit API key."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = None
            mock_genai.Client.return_value = MagicMock()

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider(api_key="my-key", model="gemini-1.5-pro")
            assert provider.model_id == "gemini-1.5-pro"


class TestGoogleProviderGenerate:
    """Tests for GoogleProvider generate methods with null responses."""

    def test_generate_text_null_raises(self):
        """generate_text should raise ValueError when text is None."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = None
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            with pytest.raises(ValueError, match="no text content"):
                provider.generate_text("test prompt")

    def test_generate_structure_null_parsed_raises(self):
        """generate_structure should raise ValueError when parsed is None."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.parsed = None
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            with pytest.raises(ValueError, match="returned None"):
                provider.generate_structure("test", SlideConfig)


    def test_generate_structure_unexpected_type_raises(self):
        """generate_structure should raise ValueError when parsed is an unexpected type."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.parsed = ["unexpected", "list"]
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            with pytest.raises(ValueError, match="unexpected type"):
                provider.generate_structure("test", SlideConfig)


class TestAnthropicProviderConstructor:
    """Tests for AnthropicProvider constructor."""

    def test_import_error_raises(self):
        """AnthropicProvider should raise ImportError when anthropic not installed."""
        import sys
        from unittest.mock import patch, MagicMock

        with patch.dict(sys.modules, {"anthropic": None}):
            from autoppt.llm_provider import AnthropicProvider
            with pytest.raises(ImportError, match="pip install anthropic"):
                AnthropicProvider(api_key="test-key")

    def test_no_api_key_raises(self):
        """AnthropicProvider should raise APIKeyError when no key provided."""
        from unittest.mock import patch, MagicMock
        from autoppt.exceptions import APIKeyError

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("anthropic.Anthropic"):
            mock_config.initialize = MagicMock()
            mock_config.ANTHROPIC_API_KEY = None

            from autoppt.llm_provider import AnthropicProvider
            with pytest.raises(APIKeyError):
                AnthropicProvider()


class TestAnthropicProviderGenerate:
    """Tests for AnthropicProvider generate methods."""

    def _make_provider(self):
        """Create a mock AnthropicProvider without hitting real APIs."""
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_generate_text_empty_content_raises(self):
        """generate_text should raise ValueError when content is empty."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_message = MagicMock()
        mock_message.content = []

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="empty response"):
                provider.generate_text("test prompt")

    def test_generate_text_returns_text(self):
        """generate_text should return the text from the first content block."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "Hello world"
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_text("test prompt")
            assert result == "Hello world"

    def test_generate_structure_empty_content_raises(self):
        """generate_structure should raise ValueError when content is empty."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_message = MagicMock()
        mock_message.content = []

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="empty response"):
                provider.generate_structure("test", SlideConfig)

    def test_generate_structure_invalid_json_raises(self):
        """generate_structure should raise ValueError for invalid JSON."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "not valid json {{"
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="invalid JSON"):
                provider.generate_structure("test", SlideConfig)

    def test_generate_structure_generic_fence_no_lang_tag(self):
        """generate_structure should strip generic ``` fences with JSON starting on first line."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = '```\n{"title":"Test","bullets":["A"],"slide_type":"content","citations":[]}\n```'
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Test"


    def test_generate_structure_max_tokens_truncation_raises(self):
        """generate_structure should raise ValueError when stop_reason is max_tokens."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = '{"title":"Truncated","bullets":["A"]}'
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "max_tokens"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="truncated"):
                provider.generate_structure("test", SlideConfig)


class TestMockProviderTypeDetection:
    """Tests for MockProvider type detection helpers."""

    def test_is_str_type_with_str(self):
        """_is_str_type should return True for str annotation."""
        from typing import Optional
        provider = MockProvider()
        # Access the inner function through generate_structure by testing outcomes
        # Instead, test indirectly via SlideConfig which has str and Optional[str] fields

        result = provider.generate_structure("topic: testing", SlideConfig)
        # title is str, should be populated
        assert isinstance(result.title, str)
        # left_title is Optional[str], should be populated
        assert result.left_title is None or isinstance(result.left_title, str)

    def test_is_list_str_type(self):
        """_is_list_str_type should populate List[str] fields."""
        provider = MockProvider()
        result = provider.generate_structure("topic: testing", SlideConfig)
        assert isinstance(result.bullets, list)
        assert all(isinstance(b, str) for b in result.bullets)

    def test_unknown_field_type_gets_none(self):
        """Fields with unrecognized types should get None via fallback branch."""
        from pydantic import BaseModel
        from typing import Optional, Dict

        class WeirdSchema(BaseModel):
            title: str
            metadata: Optional[Dict[str, int]] = None

        provider = MockProvider()
        result = provider.generate_structure("topic: testing", WeirdSchema)
        assert isinstance(result.title, str)
        # metadata has an unrecognized type, so fallback sets None
        assert result.metadata is None


class TestMockProviderSlideTypeSelection:
    """Tests for MockProvider slide_type keyword-based selection."""

    def test_quote_keyword(self):
        """Prompt with 'quote' should yield QUOTE slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("Create a quote slide about leadership", SlideConfig)
        assert result.slide_type == SlideType.QUOTE

    def test_comparison_keyword(self):
        """Prompt with 'compare' should yield COMPARISON slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("compare option A versus option B", SlideConfig)
        assert result.slide_type == SlideType.COMPARISON

    def test_two_column_keyword(self):
        """Prompt with 'framework' should yield TWO_COLUMN slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("describe the framework and pillars", SlideConfig)
        assert result.slide_type == SlideType.TWO_COLUMN

    def test_statistics_keyword(self):
        """Prompt with 'market' should yield STATISTICS slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("analyze the market data", SlideConfig)
        assert result.slide_type == SlideType.STATISTICS

    def test_image_keyword(self):
        """Prompt with 'visual' should yield IMAGE slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("show a visual representation of the topic: art", SlideConfig)
        assert result.slide_type == SlideType.IMAGE

    def test_chart_keyword(self):
        """Prompt with 'growth' should yield CHART slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("show the growth trends in data", SlideConfig)
        assert result.slide_type == SlideType.CHART

    def test_default_content_type(self):
        """Prompt with no special keywords should yield CONTENT slide type."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure("discuss the main points of the topic", SlideConfig)
        assert result.slide_type == SlideType.CONTENT

    def test_preferred_type_hint_quote(self):
        """preferred slide type hint should override keyword matching."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'quote'", SlideConfig
        )
        assert result.slide_type == SlideType.QUOTE

    def test_preferred_type_hint_comparison(self):
        """preferred slide type: 'comparison' hint."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'comparison'", SlideConfig
        )
        assert result.slide_type == SlideType.COMPARISON

    def test_preferred_type_hint_statistics(self):
        """preferred slide type: 'statistics' hint."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'statistics'", SlideConfig
        )
        assert result.slide_type == SlideType.STATISTICS

    def test_preferred_type_hint_image(self):
        """preferred slide type: 'image' hint."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'image'", SlideConfig
        )
        assert result.slide_type == SlideType.IMAGE

    def test_preferred_type_hint_chart(self):
        """preferred slide type: 'chart' hint."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'chart'", SlideConfig
        )
        assert result.slide_type == SlideType.CHART

    def test_preferred_type_hint_two_column(self):
        """preferred slide type: 'two_column' hint."""
        from autoppt.data_types import SlideType
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide. Preferred slide type: 'two_column'", SlideConfig
        )
        assert result.slide_type == SlideType.TWO_COLUMN


class TestMockProviderHints:
    """Tests for MockProvider hint extraction (left_title, right_title, quote hints)."""

    def test_title_fields_get_expected_text(self):
        """left_title and right_title get their dedicated defaults; generic title gets overview."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a two_column slide about topic: widgets. "
            "Preferred slide type: 'two_column'",
            SlideConfig,
        )
        # left_title and right_title have dedicated branches with defaults
        assert result.left_title == "Current State"
        assert result.right_title == "Future State"
        # The generic 'title' field still gets overview text
        assert "overview" in result.title.lower() or "widget" in result.title.lower()

    def test_quote_author_hint(self):
        """quote author hint should populate quote_author field with original casing."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a quote slide. Quote author hint: 'Einstein'. Quote context hint: 'Physics Lecture'. "
            "Preferred slide type: 'quote'",
            SlideConfig,
        )
        assert result.quote_author == "Einstein"
        assert result.quote_context == "Physics Lecture"

    def test_quote_author_default(self):
        """quote_author without hint should use default."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a quote slide. Preferred slide type: 'quote'",
            SlideConfig,
        )
        assert result.quote_author == "AutoPPT Research Desk"
        assert result.quote_context == "Mock analysis"


class TestGetProviderWithModel:
    """Tests for get_provider with model parameter."""

    def test_get_openai_provider_with_model(self):
        """get_provider should pass model to OpenAIProvider."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.DEFAULT_OPENAI_MODEL = "gpt-4.1"
            mock_openai_cls.return_value = MagicMock()

            provider = get_provider("openai", api_key="test-key", model="gpt-4-turbo")
            assert provider.model == "gpt-4-turbo"

    def test_get_google_provider_with_model(self):
        """get_provider should pass model to GoogleProvider."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.DEFAULT_GOOGLE_MODEL = "gemini-2.5-flash"
            mock_genai.Client.return_value = MagicMock()

            provider = get_provider("google", api_key="test-key", model="gemini-1.5-pro")
            assert provider.model_id == "gemini-1.5-pro"

    def test_get_anthropic_provider_with_model(self):
        """get_provider should pass model to AnthropicProvider."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_config.initialize = MagicMock()
            mock_config.ANTHROPIC_API_KEY = "test-key"
            mock_config.DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
            mock_anthropic_cls.return_value = MagicMock()

            provider = get_provider("anthropic", api_key="test-key", model="claude-3-5-sonnet-20241022")
            assert provider.model == "claude-3-5-sonnet-20241022"

    def test_get_provider_default_model_when_none(self):
        """get_provider should use default model when model is None."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
            mock_openai_cls.return_value = MagicMock()

            provider = get_provider("openai", api_key="test-key")
            assert provider.model == "gpt-5.4-mini"


class TestProviderHelpers:
    """Tests for module-level helper functions."""

    def test_get_supported_providers(self):
        from autoppt.llm_provider import get_supported_providers
        providers = get_supported_providers()
        assert "openai" in providers
        assert "google" in providers
        assert "anthropic" in providers
        assert "mock" in providers

    def test_get_provider_models(self):
        from autoppt.llm_provider import get_provider_models
        assert "gpt-4.1" in get_provider_models("openai")
        assert "gpt-5.4" in get_provider_models("openai")
        assert "gemini-2.5-flash" in get_provider_models("google")
        assert "gemini-2.5-flash-lite" in get_provider_models("google")
        assert "gemini-3-flash-preview" in get_provider_models("google")
        assert "gemini-3.1-pro-preview" in get_provider_models("google")
        assert "claude-sonnet-4-6" in get_provider_models("anthropic")
        assert get_provider_models("nonexistent") == []

    def test_openai_models_include_o_series(self):
        from autoppt.llm_provider import get_provider_models
        openai_models = get_provider_models("openai")
        assert "o3" in openai_models
        assert "o3-pro" in openai_models
        assert "o3-mini" in openai_models
        assert "o4-mini" in openai_models

    def test_openai_models_include_pro_variants(self):
        from autoppt.llm_provider import get_provider_models
        openai_models = get_provider_models("openai")
        assert "gpt-5.4-pro" in openai_models

    def test_anthropic_haiku_uses_alias(self):
        from autoppt.llm_provider import get_provider_models
        anthropic_models = get_provider_models("anthropic")
        assert "claude-haiku-4-5" in anthropic_models
        assert "claude-haiku-4-5-20251001" not in anthropic_models

    def test_anthropic_models_include_opus_4_7(self):
        from autoppt.llm_provider import get_provider_models
        anthropic_models = get_provider_models("anthropic")
        assert "claude-opus-4-7" in anthropic_models

    def test_anthropic_models_include_legacy_opus_4_6(self):
        from autoppt.llm_provider import get_provider_models
        anthropic_models = get_provider_models("anthropic")
        assert "claude-opus-4-6" in anthropic_models

    def test_openai_default_model_is_gpt54_mini(self):
        from autoppt.config import Config
        assert Config.DEFAULT_OPENAI_MODEL == "gpt-5.4-mini"


class TestOSeriesWarning:
    """Tests for o-series reasoning model warnings."""

    def test_o_series_model_logs_warning_on_generate_structure(self, caplog):
        """OpenAI o-series models should log a warning when generate_structure is called."""
        import logging
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value = MagicMock()

            provider = OpenAIProvider(api_key="test-key", model="o3-mini")

            mock_parsed = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.parsed = mock_parsed
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            provider.client.beta.chat.completions.parse.return_value = mock_completion

            with patch("autoppt.llm_provider.Config") as retry_config:
                retry_config.API_RETRY_ATTEMPTS = 1
                retry_config.API_RETRY_DELAY_SECONDS = 0
                with caplog.at_level(logging.WARNING, logger="autoppt.llm_provider"):
                    provider.generate_structure("test prompt", MagicMock)

            assert "Reasoning model 'o3-mini' may have limited structured output support" in caplog.text


    def test_non_o_series_model_does_not_log_warning(self, caplog):
        """Non o-series models should not trigger the structured output warning."""
        import logging
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_openai_cls.return_value = MagicMock()

            provider = OpenAIProvider(api_key="test-key", model="gpt-5.4-mini")

            mock_parsed = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.parsed = mock_parsed
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            provider.client.beta.chat.completions.parse.return_value = mock_completion

            with patch("autoppt.llm_provider.Config") as retry_config:
                retry_config.API_RETRY_ATTEMPTS = 1
                retry_config.API_RETRY_DELAY_SECONDS = 0
                with caplog.at_level(logging.WARNING, logger="autoppt.llm_provider"):
                    provider.generate_structure("test prompt", MagicMock)

            assert "Reasoning model" not in caplog.text


class TestRetryAttemptsGuard:
    """Tests for _run_with_retries when API_RETRY_ATTEMPTS < 1."""

    def test_retry_attempts_less_than_one_raises(self):
        """_run_with_retries should raise ValueError when API_RETRY_ATTEMPTS < 1."""
        from autoppt.llm_provider import _run_with_retries
        from unittest.mock import patch

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 0
            mock_config.API_RETRY_DELAY_SECONDS = 0

            with pytest.raises(ValueError, match="API_RETRY_ATTEMPTS must be >= 1"):
                _run_with_retries("test", lambda: "should not run")


class TestAnthropicNoTextBlock:
    """Tests for Anthropic provider when content blocks have no .text attribute."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_generate_text_no_text_block_raises(self):
        """generate_text should raise ValueError when no block has .text attribute."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        # Use spec=[] so MagicMock does NOT auto-create .text
        tool_block = MagicMock(spec=[])
        mock_message = MagicMock()
        mock_message.content = [tool_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="no text block"):
                provider.generate_text("test prompt")

    def test_generate_structure_no_text_block_raises(self):
        """generate_structure should raise ValueError when no block has .text attribute."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        tool_block = MagicMock(spec=[])
        mock_message = MagicMock()
        mock_message.content = [tool_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            with pytest.raises(ValueError, match="no text block"):
                provider.generate_structure("test", SlideConfig)

    def test_generate_text_skips_non_text_block_returns_later_text(self):
        """generate_text should skip blocks without .text and return text from a later block."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        # First block: no .text attribute (e.g., tool_use block)
        tool_block = MagicMock(spec=[])
        # Second block: has .text attribute
        text_block = MagicMock()
        text_block.text = "Real answer from second block"

        mock_message = MagicMock()
        mock_message.content = [tool_block, text_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_text("test prompt")
            assert result == "Real answer from second block"


class TestIsStrTypeWithNoneType:
    """Test _is_str_type returns False for type(None) annotation (line 306)."""

    def test_nonetype_field_gets_none(self):
        """A schema field annotated with NoneType should get None from MockProvider."""
        from pydantic import BaseModel
        from typing import Optional

        class SchemaWithNone(BaseModel):
            title: str
            nothing: None = None  # annotation is type(None)

        provider = MockProvider()
        result = provider.generate_structure("topic: test", SchemaWithNone)
        assert isinstance(result.title, str)
        # NoneType is not str, not list, not section, etc. -> falls to else -> None
        assert result.nothing is None


class TestMockProviderLeftRightTitleHints:
    """Tests for left_title_hint / right_title_hint extraction in MockProvider."""

    def test_left_and_right_title_hints_extracted(self):
        """Prompt with left/right title hints should be extractable via _extract_hint."""
        provider = MockProvider()
        prompt = (
            "Create a slide about topic: widgets. "
            "Left title hint: 'before'. Right title hint: 'after'. "
            "Preferred slide type: 'two_column'"
        )
        prompt_lower = prompt.lower()
        left_hint = provider._extract_hint(prompt_lower, "left title hint")
        right_hint = provider._extract_hint(prompt_lower, "right title hint")
        assert left_hint == "before"
        assert right_hint == "after"

    def test_left_right_title_hints_via_custom_schema(self):
        """Use a custom schema where left_title/right_title don't contain 'title' in name."""
        from pydantic import BaseModel
        from typing import Optional

        class TwoColumnSchema(BaseModel):
            title: str
            left_heading: str  # not matching "title" substring
            right_heading: str

        provider = MockProvider()
        # The hints won't apply to these field names since the MockProvider
        # only checks left_title_hint for field_name == "left_title",
        # but we verify the hint extraction works correctly.
        prompt_lower = "left title hint: 'before'. right title hint: 'after'."
        assert provider._extract_hint(prompt_lower, "left title hint") == "before"
        assert provider._extract_hint(prompt_lower, "right title hint") == "after"

    def test_extract_hint_missing_returns_empty(self):
        """_extract_hint should return empty string when hint is not in prompt."""
        provider = MockProvider()
        assert provider._extract_hint("some prompt text", "left title hint") == ""
        assert provider._extract_hint("some prompt text", "right title hint") == ""


class TestOpenAIBuildMessages:
    """Tests for OpenAIProvider._build_messages helper."""

    def test_build_messages_with_system_prompt(self):
        msgs = OpenAIProvider._build_messages("hello", "you are helpful")
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "you are helpful"}
        assert msgs[1] == {"role": "user", "content": "hello"}

    def test_build_messages_without_system_prompt(self):
        msgs = OpenAIProvider._build_messages("hello", "")
        assert len(msgs) == 1
        assert msgs[0] == {"role": "user", "content": "hello"}

    def test_build_messages_empty_system_prompt_excluded(self):
        """Empty string system prompt should not produce a system message."""
        msgs = OpenAIProvider._build_messages("test", "")
        for m in msgs:
            assert m["role"] != "system"


class TestAnthropicBaseUrlWarning:
    """Tests for Anthropic provider base_url logging."""

    def test_non_local_base_url_detected(self):
        """_is_local_base_url should distinguish local from remote URLs."""
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://localhost:8080") is True
        assert _is_local_base_url("http://127.0.0.1:8080") is True
        assert _is_local_base_url("https://api.anthropic.com") is False
        assert _is_local_base_url(None) is False


class TestOpenAIEmptyChoices:
    """Tests for OpenAI provider with empty choices list."""

    def test_generate_text_empty_choices_raises(self):
        """generate_text should raise ValueError when choices is empty."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = MagicMock(choices=[])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            with pytest.raises(ValueError, match="no choices"):
                provider.generate_text("test prompt")

    def test_generate_structure_empty_choices_raises(self):
        """generate_structure should raise ValueError when choices is empty."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            with pytest.raises(ValueError, match="no choices"):
                provider.generate_structure("test", SlideConfig)


class TestGoogleBlockedResponses:
    """Tests for Google provider blocked/safety-filtered responses."""

    def test_generate_text_blocked_raises(self):
        """generate_text should raise ValueError when response.text raises."""
        from unittest.mock import patch, MagicMock, PropertyMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            type(mock_response).text = PropertyMock(side_effect=ValueError("Safety blocked"))
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            with pytest.raises(ValueError, match="blocked or empty"):
                provider.generate_text("test prompt")

    def test_generate_structure_blocked_raises(self):
        """generate_structure should raise when response.parsed raises."""
        from unittest.mock import patch, MagicMock, PropertyMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            type(mock_response).parsed = PropertyMock(side_effect=ValueError("Safety blocked"))
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            with pytest.raises(ValueError, match="blocked or empty"):
                provider.generate_structure("test", SlideConfig)

    def test_generate_structure_dict_response(self):
        """generate_structure should handle dict response via model_validate."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            # Return a raw dict instead of a Pydantic model
            mock_response.parsed = {
                "title": "Test Slide",
                "slide_type": "content",
                "bullets": ["Point A", "Point B"],
            }
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Test Slide"



class TestRunWithRetriesRateLimitExhausted:
    """Test _run_with_retries raises RateLimitError when retries exhausted."""

    def test_rate_limit_exhausted_raises(self):
        """Single retry attempt with rate-limit error should raise RateLimitError."""
        from unittest.mock import patch
        from autoppt.llm_provider import _run_with_retries
        from autoppt.exceptions import RateLimitError

        class HTTPError(Exception):
            status_code = 429

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            with pytest.raises(RateLimitError):
                _run_with_retries("test", lambda: (_ for _ in ()).throw(HTTPError("rate limited")))


class TestBaseLLMProviderAbstract:
    """Test that BaseLLMProvider cannot be instantiated directly."""

    def test_instantiation_raises_type_error(self):
        """Instantiating BaseLLMProvider should raise TypeError."""
        with pytest.raises(TypeError):
            BaseLLMProvider()


class TestOpenAIImportError:
    """Test OpenAIProvider raises ImportError when openai is not installed."""

    def test_import_error_raised(self):
        """OpenAIProvider should raise ImportError when openai package is missing."""
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"openai": None}):
            from autoppt.llm_provider import OpenAIProvider
            with pytest.raises(ImportError, match="pip install openai"):
                OpenAIProvider(api_key="test-key")


class TestOpenAIGenerateTextReturnsContent:
    """Test OpenAI generate_text returns content successfully (line 135)."""

    def test_generate_text_returns_content(self):
        """generate_text should return the content string on success."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from OpenAI"
            mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            result = provider.generate_text("test prompt")
            assert result == "Hello from OpenAI"


class TestOpenAIGenerateStructureReturnsParsed:
    """Test OpenAI generate_structure returns parsed result (line 152)."""

    def test_generate_structure_returns_parsed(self):
        """generate_structure should return the parsed object on success."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("openai.OpenAI") as mock_openai_cls:
            mock_config.initialize = MagicMock()
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            fake_parsed = SlideConfig(
                title="Test", bullets=["A"], slide_type="content"
            )
            mock_choice = MagicMock()
            mock_choice.message.parsed = fake_parsed
            mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

            from autoppt.llm_provider import OpenAIProvider
            provider = OpenAIProvider()
            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Test"


class TestGoogleImportError:
    """Test GoogleProvider raises ImportError when google.genai is missing."""

    def test_import_error_raised(self):
        """GoogleProvider should raise ImportError when google-genai package is missing."""
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"google": None, "google.genai": None}):
            from autoppt.llm_provider import GoogleProvider
            with pytest.raises(ImportError, match="pip install google-genai"):
                GoogleProvider(api_key="test-key")


class TestGoogleGenerateTextReturnsText:
    """Test Google generate_text returns text successfully (line 188)."""

    def test_generate_text_returns_text(self):
        """generate_text should return the text string on success."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Hello from Google"
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            result = provider.generate_text("test prompt")
            assert result == "Hello from Google"


class TestGoogleGenerateStructureReturnsParsed:
    """Test Google generate_structure returns parsed non-dict (line 213)."""

    def test_generate_structure_returns_parsed_model(self):
        """generate_structure should return parsed directly when it is not a dict."""
        from unittest.mock import patch, MagicMock

        with patch("autoppt.llm_provider.Config") as mock_config, \
             patch("google.genai") as mock_genai:
            mock_config.initialize = MagicMock()
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            # Return a proper Pydantic model instance (not a dict)
            fake_parsed = SlideConfig(
                title="Google Slide", bullets=["X"], slide_type="content"
            )
            mock_response.parsed = fake_parsed
            mock_client.models.generate_content.return_value = mock_response

            from autoppt.llm_provider import GoogleProvider
            provider = GoogleProvider()
            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Google Slide"


class TestAnthropicGenerateTextWithSystemPrompt:
    """Test Anthropic generate_text passes system_prompt in kwargs (line 241)."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_system_prompt_passed_in_kwargs(self):
        """generate_text with non-empty system_prompt should include 'system' key."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = "response with system"
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_text("test prompt", system_prompt="Be helpful")
            assert result == "response with system"

            # Verify system prompt was passed
            call_kwargs = provider.client.messages.create.call_args[1]
            assert call_kwargs["system"] == "Be helpful"


class TestAnthropicGenerateStructureWithSystemPrompt:
    """Test Anthropic generate_structure passes system_prompt in kwargs (line 272)."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_system_prompt_passed_in_kwargs(self):
        """generate_structure with non-empty system_prompt should include 'system' key."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        mock_block = MagicMock()
        mock_block.text = '{"title":"Test","bullets":["A"],"slide_type":"content","citations":[]}'
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_structure("test", SlideConfig, system_prompt="Be structured")
            assert result.title == "Test"

            # Verify system prompt was passed
            call_kwargs = provider.client.messages.create.call_args[1]
            assert call_kwargs["system"] == "Be structured"


class TestMockProviderLeftRightTitleDefault:
    """Test MockProvider left_title/right_title defaults (lines 387, 389)."""

    def test_left_right_title_defaults(self):
        """left_title and right_title should use defaults when no hints provided."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create a slide about topic: widgets. Preferred slide type: 'two_column'",
            SlideConfig,
        )
        # The left_title field matches "title" in field_name.lower() so it takes
        # the title branch. But field_name == "left_title" is checked specifically
        # on line 386. Let's verify the values are set.
        assert result.left_title is not None
        assert result.right_title is not None


class TestMockProviderOptionalListStr:
    """Test MockProvider _is_list_str_type with Optional[List[str]] (line 362)."""

    def test_optional_list_str_field(self):
        """Optional[List[str]] fields should be populated by MockProvider."""
        from pydantic import BaseModel
        from typing import Optional, List

        class SchemaWithOptionalList(BaseModel):
            title: str
            tags: Optional[List[str]] = None

        provider = MockProvider()
        result = provider.generate_structure("topic: testing", SchemaWithOptionalList)
        assert isinstance(result.title, str)
        assert isinstance(result.tags, list)
        assert len(result.tags) > 0
        assert all(isinstance(t, str) for t in result.tags)


class TestTransientErrorRetry:
    """Tests for transient server error retry logic."""

    def test_transient_500_error_is_retried(self):
        """500 errors should be retried."""
        from autoppt.llm_provider import _is_transient_error

        class FakeError(Exception):
            status_code = 500

        assert _is_transient_error(FakeError("server error")) is True

    def test_transient_502_error_is_retried(self):
        """502 errors should be retried."""
        from autoppt.llm_provider import _is_transient_error

        class FakeError(Exception):
            status_code = 502

        assert _is_transient_error(FakeError("bad gateway")) is True

    def test_transient_timeout_in_message_is_retried(self):
        """Connection timeout errors identified by message should be retried."""
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("Connection timed out")) is True

    def test_non_transient_400_not_retried(self):
        """400 errors should NOT be retried."""
        from autoppt.llm_provider import _is_transient_error

        class FakeError(Exception):
            status_code = 400

        assert _is_transient_error(FakeError("bad request")) is False

    def test_run_with_retries_retries_transient_error(self):
        """_run_with_retries should retry on transient server errors."""
        from unittest.mock import patch
        from autoppt.llm_provider import _run_with_retries
        from autoppt.config import Config

        call_count = 0

        class ServerError(Exception):
            status_code = 503

        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ServerError("Service Unavailable")
            return "success"

        original_attempts = Config.API_RETRY_ATTEMPTS
        original_delay = Config.API_RETRY_DELAY_SECONDS
        Config.API_RETRY_ATTEMPTS = 3
        Config.API_RETRY_DELAY_SECONDS = 0
        try:
            with patch("autoppt.llm_provider.time.sleep"):
                result = _run_with_retries("test", flaky_operation)
            assert result == "success"
            assert call_count == 3
        finally:
            Config.API_RETRY_ATTEMPTS = original_attempts
            Config.API_RETRY_DELAY_SECONDS = original_delay


class TestRateLimitDetection:
    """Test improved rate limit error detection."""

    def test_rate_limit_detection_matches_real_rate_limit(self):
        """A real rate limit error message should be detected."""
        from autoppt.llm_provider import _is_rate_limit_error
        assert _is_rate_limit_error(Exception("rate_limit_exceeded")) is True
        assert _is_rate_limit_error(Exception("Rate limit reached")) is True


class TestTransientErrorDetectionPrecision:
    """Test that transient error detection is precise enough to avoid false positives."""

    def test_bare_connection_not_transient(self):
        """Bare 'connection' in message should NOT trigger transient detection."""
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("database connection pool exhausted")) is False

    def test_connection_reset_is_transient(self):
        """'Connection reset' should be detected as transient."""
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("Connection reset by peer")) is True

    def test_connection_refused_is_transient(self):
        """'Connection refused' should be detected as transient."""
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("Connection refused")) is True

    def test_bad_gateway_message_is_transient(self):
        """'bad gateway' in message should be detected as transient."""
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(Exception("502 bad gateway")) is True


class TestAnthropicTruncationWarning:
    """Test that Anthropic logs a warning when response is truncated (max_tokens)."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_truncation_raises_error(self):
        """When stop_reason is 'max_tokens', a ValueError should be raised."""
        import json
        from unittest.mock import MagicMock, patch

        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = json.dumps({"title": "Test", "bullets": ["A"]})

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "max_tokens"

        with patch("autoppt.llm_provider._run_with_retries", return_value=mock_message):
            with pytest.raises(ValueError, match="truncated"):
                provider.generate_structure("test", SlideConfig)

    def test_non_truncated_response_succeeds(self):
        """When stop_reason is 'end_turn', parsing should succeed normally."""
        import json
        from unittest.mock import MagicMock, patch

        provider = self._make_provider()

        mock_block = MagicMock()
        mock_block.text = json.dumps({"title": "Test", "bullets": ["A"]})

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "end_turn"

        with patch("autoppt.llm_provider._run_with_retries", return_value=mock_message):
            result = provider.generate_structure("test", SlideConfig)
        assert result.title == "Test"


class TestMockProviderLeftRightTitleFallbacks:
    """Test MockProvider default values for left_title and right_title when no hints are in the prompt."""

    def test_left_title_default_when_no_hint(self):
        """left_title should default to 'Current State' when no hint is provided."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create slide about Machine Learning",
            SlideConfig,
        )
        assert result.left_title == "Current State"

    def test_right_title_default_when_no_hint(self):
        """right_title should default to 'Future State' when no hint is provided."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create slide about Machine Learning",
            SlideConfig,
        )
        assert result.right_title == "Future State"

    def test_left_title_uses_hint_when_provided(self):
        """left_title should use the hint when provided in the prompt."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create slide about ML. Left title hint: 'Before Change'",
            SlideConfig,
        )
        assert result.left_title == "Before Change"

    def test_right_title_uses_hint_when_provided(self):
        """right_title should use the hint when provided in the prompt."""
        provider = MockProvider()
        result = provider.generate_structure(
            "Create slide about ML. Right title hint: 'After Change'",
            SlideConfig,
        )
        assert result.right_title == "After Change"


class TestAnthropicJsonFallbackViaGenerateStructure:
    """Test that the JSON raw_decode fallback path in generate_structure is exercised."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_raw_decode_fallback_extracts_json_with_trailing_text(self):
        """When response has valid JSON followed by trailing text, raw_decode should extract it."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        # This text is NOT valid JSON as a whole (due to trailing text),
        # so json.loads will fail and the raw_decode fallback path (line 335) fires.
        raw_response = (
            'Here is the output: {"title": "Fallback Test", "bullets": ["A", "B"], '
            '"speaker_notes": "", "image_prompt": "", "left_title": "", "right_title": ""} '
            'I hope this helps!'
        )
        mock_block = MagicMock()
        mock_block.text = raw_response
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "end_turn"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Fallback Test"
            assert result.bullets == ["A", "B"]

    def test_raw_decode_fallback_skips_invalid_brace_finds_valid_json(self):
        """When first '{' is not valid JSON, raw_decode should skip it and find the real JSON."""
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        # The first '{field}' is not valid JSON; the second '{...}' is.
        raw_response = (
            'Note: {field} is important. {"title": "Found It", "bullets": ["X"], '
            '"speaker_notes": "", "image_prompt": "", "left_title": "", "right_title": ""}'
        )
        mock_block = MagicMock()
        mock_block.text = raw_response
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "end_turn"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Found It"


class TestRawDecodePicksLargestObject:
    """Test that raw_decode fallback picks the largest JSON object."""

    def _make_provider(self):
        from unittest.mock import MagicMock
        from autoppt.llm_provider import AnthropicProvider

        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"
        return provider

    def test_picks_largest_object_over_smaller_nested(self):
        from unittest.mock import patch, MagicMock

        provider = self._make_provider()
        # Small object first, large (correct) object second
        raw_response = (
            'prefix {"x": 1} then '
            '{"title": "Correct", "bullets": ["A", "B"], '
            '"speaker_notes": "", "image_prompt": ""}'
        )
        mock_block = MagicMock()
        mock_block.text = raw_response
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "end_turn"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message

            result = provider.generate_structure("test", SlideConfig)
            assert result.title == "Correct"
            assert result.bullets == ["A", "B"]


class TestRawDecodeWarningLog:
    """Tests that the raw_decode fallback logs a warning."""

    def test_raw_decode_fallback_logs_warning(self):
        from unittest.mock import patch, MagicMock
        from autoppt.llm_provider import AnthropicProvider

        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.client = MagicMock()
        provider.model = "claude-test"

        raw_response = (
            'Explanation text {"title": "Test", "bullets": ["A"], '
            '"speaker_notes": "", "image_prompt": ""} trailing text'
        )
        mock_block = MagicMock()
        mock_block.text = raw_response
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.stop_reason = "end_turn"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 1
            mock_config.API_RETRY_DELAY_SECONDS = 0
            provider.client.messages.create.return_value = mock_message
            with patch("autoppt.llm_provider.logger") as mock_logger:
                result = provider.generate_structure("test", SlideConfig)
                assert result.title == "Test"
                mock_logger.warning.assert_called()
                assert any(
                    "raw_decode fallback" in str(call)
                    for call in mock_logger.warning.call_args_list
                )


class TestOpenAIBaseURLWarning:
    """Tests for OPENAI_API_BASE non-local URL warning."""

    def test_non_local_base_url_logs_warning(self):
        """Non-local OPENAI_API_BASE should log a warning."""
        from unittest.mock import patch, MagicMock

        mock_openai_cls = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_BASE": "https://custom.api.example.com"}):
            with patch("autoppt.llm_provider.Config") as mock_config:
                mock_config.OPENAI_API_KEY = "test-key"
                mock_config.initialize.return_value = None
                with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_cls)}):
                    with patch("autoppt.llm_provider.logger") as mock_logger:
                        OpenAIProvider(api_key="test-key")
                        mock_logger.warning.assert_called_once()
                        assert "Non-local OpenAI base URL" in mock_logger.warning.call_args[0][0]

    def test_local_base_url_no_warning(self):
        """Local OPENAI_API_BASE should not log a warning."""
        from unittest.mock import patch, MagicMock

        mock_openai_cls = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_BASE": "http://localhost:8080"}):
            with patch("autoppt.llm_provider.Config") as mock_config:
                mock_config.OPENAI_API_KEY = "test-key"
                mock_config.initialize.return_value = None
                with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_cls)}):
                    with patch("autoppt.llm_provider.logger") as mock_logger:
                        OpenAIProvider(api_key="test-key")
                        mock_logger.warning.assert_not_called()


class TestRetryExhaustion:
    """Test that all retries exhausted properly raises RateLimitError."""

    def test_all_retries_exhausted_raises_rate_limit_error(self):
        from autoppt.llm_provider import _run_with_retries
        from autoppt.exceptions import RateLimitError
        from unittest.mock import patch

        def always_rate_limited():
            raise Exception("429 rate limit exceeded")

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 0
            with pytest.raises(RateLimitError):
                _run_with_retries("test", always_rate_limited)

    def test_transient_error_retried(self):
        from autoppt.llm_provider import _run_with_retries
        from unittest.mock import patch

        call_count = 0

        def transient_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("connection reset by peer")
            return "recovered"

        with patch("autoppt.llm_provider.Config") as mock_config:
            mock_config.API_RETRY_ATTEMPTS = 3
            mock_config.API_RETRY_DELAY_SECONDS = 1
            mock_config.TRANSIENT_RETRY_BASE_SECONDS = 0
            result = _run_with_retries("test", transient_then_ok)

        assert result == "recovered"
        assert call_count == 2

    def test_transient_error_detection(self):
        from autoppt.llm_provider import _is_transient_error
        assert _is_transient_error(ConnectionError("connection reset")) is True
        assert _is_transient_error(Exception("timed out")) is True
        assert _is_transient_error(TypeError("wrong type")) is False


class TestIsLocalBaseUrl:
    """Tests for _is_local_base_url function."""

    def test_localhost(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://localhost:8080/v1") is True

    def test_127_0_0_1(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://127.0.0.1:1234/v1") is True

    def test_ipv6_loopback(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://[::1]:8080/v1") is True

    def test_0_0_0_0(self):
        """_is_local_base_url should recognize 0.0.0.0 as local."""
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("http://0.0.0.0:11434/v1") is True

    def test_remote_url(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url("https://api.example.com/v1") is False

    def test_none(self):
        from autoppt.llm_provider import _is_local_base_url
        assert _is_local_base_url(None) is False
