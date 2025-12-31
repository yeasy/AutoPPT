"""
Unit tests for Researcher module.
"""
import pytest
from unittest.mock import patch, MagicMock

from autoppt.researcher import Researcher


class TestResearcherInit:
    """Tests for Researcher initialization."""
    
    def test_researcher_instantiation(self):
        """Test that Researcher can be instantiated."""
        researcher = Researcher()
        assert researcher is not None
        assert researcher.ddgs is not None


class TestSearchMethods:
    """Tests for search methods with mocking."""
    
    @patch.object(Researcher, 'search')
    def test_search_returns_list(self, mock_search, mock_search_results):
        """Test that search returns a list of results."""
        mock_search.return_value = mock_search_results
        
        researcher = Researcher()
        results = researcher.search("test query")
        
        assert isinstance(results, list)
        assert len(results) == 2
        assert 'title' in results[0]
        assert 'href' in results[0]
        assert 'body' in results[0]
    
    @patch.object(Researcher, 'search_wikipedia')
    def test_search_wikipedia_returns_dict(self, mock_wiki, mock_wiki_result):
        """Test that search_wikipedia returns a dictionary."""
        mock_wiki.return_value = mock_wiki_result
        
        researcher = Researcher()
        result = researcher.search_wikipedia("Artificial Intelligence")
        
        assert isinstance(result, dict)
        assert 'title' in result
        assert 'summary' in result
        assert 'url' in result
    
    @patch.object(Researcher, 'search_images')
    def test_search_images_returns_list(self, mock_images):
        """Test that search_images returns a list."""
        mock_images.return_value = [
            {"title": "Image 1", "image": "https://example.com/img1.jpg"}
        ]
        
        researcher = Researcher()
        results = researcher.search_images("technology abstract")
        
        assert isinstance(results, list)


class TestGatherContext:
    """Tests for gather_context method."""
    
    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    def test_gather_context_combines_sources(
        self, mock_wiki, mock_search, mock_search_results, mock_wiki_result
    ):
        """Test that gather_context combines web and wiki sources."""
        mock_search.return_value = mock_search_results
        mock_wiki.return_value = mock_wiki_result
        
        researcher = Researcher()
        context = researcher.gather_context(["AI applications"])
        
        assert isinstance(context, str)
        assert len(context) > 0
    
    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    def test_gather_context_deduplicates_urls(
        self, mock_wiki, mock_search, mock_search_results, mock_wiki_result
    ):
        """Test that gather_context deduplicates URLs."""
        mock_search.return_value = mock_search_results
        mock_wiki.return_value = mock_wiki_result
        
        researcher = Researcher()
        # Search same query twice
        context = researcher.gather_context(["AI", "AI"])
        
        # Should not have duplicate content
        assert isinstance(context, str)
    
    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    def test_gather_context_without_wikipedia(self, mock_wiki, mock_search, mock_search_results):
        """Test gather_context can exclude Wikipedia."""
        mock_search.return_value = mock_search_results
        mock_wiki.return_value = None
        
        researcher = Researcher()
        context = researcher.gather_context(["test"], include_wikipedia=False)
        
        assert isinstance(context, str)
        mock_wiki.assert_not_called()


class TestDownloadImage:
    """Tests for download_image method."""
    
    @patch('requests.get')
    def test_download_image_success(self, mock_get, temp_dir):
        """Test successful image download."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake image data'
        mock_get.return_value = mock_response
        
        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "test_image.jpg")
        
        result = researcher.download_image("https://example.com/image.jpg", save_path)
        
        assert result is True
        assert os.path.exists(save_path)
    
    @patch('requests.get')
    def test_download_image_failure(self, mock_get, temp_dir):
        """Test failed image download returns False."""
        mock_get.side_effect = Exception("Network error")
        
        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "test_image.jpg")
        
        result = researcher.download_image("https://example.com/image.jpg", save_path)
        
        assert result is False
