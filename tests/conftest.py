"""
Pytest configuration and shared fixtures for AutoPPT tests.
"""
import pytest
import os
import sys
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def sample_topic():
    """Return a sample topic for testing."""
    return "Artificial Intelligence"


@pytest.fixture
def sample_bullets():
    """Return sample bullet points for testing."""
    return [
        "First key point about the topic",
        "Second important insight",
        "Third critical observation"
    ]


@pytest.fixture
def mock_search_results():
    """Return mock search results for testing."""
    return [
        {
            "title": "Test Article 1",
            "href": "https://example.com/article1",
            "body": "This is the body content of article 1."
        },
        {
            "title": "Test Article 2",
            "href": "https://example.com/article2",
            "body": "This is the body content of article 2."
        }
    ]


@pytest.fixture
def mock_wiki_result():
    """Return mock Wikipedia result for testing."""
    return {
        "title": "Artificial Intelligence",
        "summary": "Artificial intelligence (AI) is intelligence demonstrated by machines.",
        "url": "https://en.wikipedia.org/wiki/Artificial_intelligence"
    }
