"""
Unit tests for LLM providers.
"""
import pytest
from typing import List

from core.llm_provider import (
    BaseLLMProvider,
    MockProvider,
    get_provider
)
from core.data_types import (
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


class TestProviderInterface:
    """Tests for BaseLLMProvider interface compliance."""
    
    def test_mock_provider_has_required_methods(self):
        """Test MockProvider has all required methods."""
        provider = MockProvider()
        
        assert hasattr(provider, 'generate_text')
        assert hasattr(provider, 'generate_structure')
        assert callable(provider.generate_text)
        assert callable(provider.generate_structure)
