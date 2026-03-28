"""
Unit tests for LLM providers.
"""
import pytest
from typing import List

from autoppt.llm_provider import (
    BaseLLMProvider,
    MockProvider,
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
