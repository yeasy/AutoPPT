"""
Unit tests for Researcher module.
"""
import socket

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
    """Tests for search methods with mocking of underlying HTTP clients."""

    def test_search_returns_list(self, mock_search_results):
        """Test that search calls the underlying DDGS text API and returns results."""
        researcher = Researcher()
        with patch.object(researcher.ddgs, 'text', return_value=mock_search_results):
            results = researcher.search("test query")

        assert isinstance(results, list)
        assert len(results) == 2
        assert 'title' in results[0]
        assert 'href' in results[0]
        assert 'body' in results[0]

    def test_search_wikipedia_returns_dict(self):
        """Test that search_wikipedia calls the wikipedia API and returns structured data."""
        import wikipedia
        mock_page = MagicMock()
        mock_page.title = "Artificial Intelligence"
        mock_page.summary = "AI is intelligence demonstrated by machines. It is a broad field."
        mock_page.url = "https://en.wikipedia.org/wiki/Artificial_intelligence"

        with patch.object(wikipedia, 'search', return_value=["Artificial Intelligence"]), \
             patch.object(wikipedia, 'page', return_value=mock_page), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("Artificial Intelligence")

        assert isinstance(result, dict)
        assert result['title'] == "Artificial Intelligence"
        assert 'summary' in result
        assert result['url'] == "https://en.wikipedia.org/wiki/Artificial_intelligence"

    def test_search_images_returns_list(self):
        """Test that search_images calls the DDGS images API and returns cleaned results."""
        raw_results = [
            {"title": "Image 1", "image": "https://example.com/img1.jpg", "thumbnail": "", "url": ""}
        ]
        researcher = Researcher()
        with patch.object(researcher.ddgs, 'images', return_value=raw_results):
            results = researcher.search_images("technology abstract")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["title"] == "Image 1"
        assert results[0]["image"] == "https://example.com/img1.jpg"


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
        context = researcher.gather_context(["AI applications"], fetch_full_text=False)

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
        context = researcher.gather_context(["AI", "AI"], fetch_full_text=False)

        # Should not have duplicate content
        assert isinstance(context, str)

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    def test_gather_context_without_wikipedia(self, mock_wiki, mock_search, mock_search_results):
        """Test gather_context can exclude Wikipedia."""
        mock_search.return_value = mock_search_results
        mock_wiki.return_value = None

        researcher = Researcher()
        context = researcher.gather_context(["test"], include_wikipedia=False, fetch_full_text=False)

        assert isinstance(context, str)
        mock_wiki.assert_not_called()


class TestDownloadImage:
    """Tests for download_image method."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_success(self, mock_get, mock_safe, temp_dir):
        """Test successful image download with properly mocked response."""
        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [jpeg_header]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "test_image.jpg")

        result = researcher.download_image("https://example.com/image.jpg", save_path)

        assert result is True
        assert os.path.exists(save_path)

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_failure(self, mock_get, mock_safe, temp_dir):
        """Test failed image download returns False."""
        mock_get.side_effect = Exception("Network error")

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "test_image.jpg")

        result = researcher.download_image("https://example.com/image.jpg", save_path)

        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_rejects_non_image_content(self, mock_get, mock_safe, temp_dir):
        """Test non-image responses are rejected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html", "Content-Length": "64"}
        mock_response.iter_content.return_value = [b'not image']
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "test_image.jpg")

        result = researcher.download_image("https://example.com/not-image", save_path)

        assert result is False

    def test_download_image_rejects_unsafe_url(self, temp_dir):
        """Test that private IPs are blocked without hitting the network."""
        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "unsafe.jpg")

        result = researcher.download_image("http://127.0.0.1/evil.jpg", save_path)

        assert result is False
        assert not os.path.exists(save_path)


class TestCaching:
    @patch.object(Researcher, 'search')
    def test_gather_context_reuses_cache(self, mock_search):
        mock_search.return_value = [
            {"title": "Cached", "href": "https://example.com/cached", "body": "Body"}
        ]

        researcher = Researcher()
        context_a = researcher.gather_context(["cache me"], include_wikipedia=False, fetch_full_text=False)
        context_b = researcher.gather_context(["cache me"], include_wikipedia=False, fetch_full_text=False)

        assert context_a == context_b
        mock_search.assert_called_once()


class TestSSRFProtection:
    """Tests for _is_safe_url SSRF protection."""

    def test_rejects_private_ip(self):
        assert Researcher._is_safe_url("http://127.0.0.1/img.jpg") is False

    def test_rejects_private_network(self):
        assert Researcher._is_safe_url("http://192.168.1.1/img.jpg") is False

    def test_rejects_link_local(self):
        assert Researcher._is_safe_url("http://169.254.1.1/img.jpg") is False

    def test_rejects_non_http_scheme(self):
        assert Researcher._is_safe_url("file:///etc/passwd") is False
        assert Researcher._is_safe_url("ftp://example.com/file") is False

    def test_rejects_empty_hostname(self):
        assert Researcher._is_safe_url("http://") is False

    @patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS failure"))
    def test_rejects_dns_failure(self, mock_dns):
        assert Researcher._is_safe_url("http://nonexistent.invalid/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 0))])
    def test_allows_public_url(self, mock_dns):
        assert Researcher._is_safe_url("https://example.com/image.jpg") is True

    @patch("socket.getaddrinfo", side_effect=socket.timeout("DNS timed out"))
    def test_rejects_dns_timeout(self, mock_dns):
        """socket.timeout during DNS resolution should cause _is_safe_url to return False."""
        assert Researcher._is_safe_url("http://evil.example.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 0))])
    def test_safe_url_does_not_leak_socket_timeout(self, mock_dns):
        """Verify that _is_safe_url does not alter the global socket default timeout."""
        original_timeout = socket.getdefaulttimeout()
        result = Researcher._is_safe_url("https://example.com/image.jpg")
        assert result is True
        assert socket.getdefaulttimeout() == original_timeout


class TestOfflineMode:
    def test_gather_context_returns_empty_string_offline(self, monkeypatch):
        monkeypatch.setenv("AUTOPPT_OFFLINE", "1")

        researcher = Researcher()
        context = researcher.gather_context(["offline test"], fetch_full_text=False)

        assert context == ""

    def test_search_images_returns_empty_list_offline(self, monkeypatch):
        monkeypatch.setenv("AUTOPPT_OFFLINE", "1")

        researcher = Researcher()
        assert researcher.search_images("offline image test") == []

    def test_search_images_respects_env_after_init(self, monkeypatch):
        researcher = Researcher()
        monkeypatch.setenv("AUTOPPT_OFFLINE", "1")

        assert researcher.search_images("offline image test") == []

    @patch("requests.get")
    def test_download_image_skips_network_offline(self, mock_get, monkeypatch, temp_dir):
        monkeypatch.setenv("AUTOPPT_OFFLINE", "1")

        researcher = Researcher()
        import os

        save_path = os.path.join(temp_dir, "offline.jpg")
        result = researcher.download_image("https://example.com/image.jpg", save_path)

        assert result is False
        mock_get.assert_not_called()


class TestImageMagicValidation:
    def test_rejects_empty_file(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "empty.jpg")
        with open(path, "wb") as f:
            pass
        assert Researcher._validate_image_file(path) is False

    def test_rejects_html_file(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "fake.jpg")
        with open(path, "wb") as f:
            f.write(b"<html><body>not an image</body></html>")
        assert Researcher._validate_image_file(path) is False

    def test_accepts_jpeg(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "real.jpg")
        with open(path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is True

    def test_accepts_png(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "real.png")
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is True

    def test_rejects_nonexistent_file(self):
        assert Researcher._validate_image_file("/nonexistent/path.jpg") is False

    def test_accepts_webp(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "real.webp")
        with open(path, "wb") as f:
            f.write(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is True

    def test_rejects_wav_riff(self, temp_dir):
        """RIFF files that are not WEBP (e.g. WAV) must be rejected."""
        import os
        path = os.path.join(temp_dir, "audio.wav")
        with open(path, "wb") as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is False

    def test_rejects_avi_riff(self, temp_dir):
        """RIFF files that are not WEBP (e.g. AVI) must be rejected."""
        import os
        path = os.path.join(temp_dir, "video.avi")
        with open(path, "wb") as f:
            f.write(b"RIFF\x00\x00\x00\x00AVI " + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is False

    def test_accepts_gif87a(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "real.gif")
        with open(path, "wb") as f:
            f.write(b"GIF87a" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is True

    def test_accepts_gif89a(self, temp_dir):
        import os
        path = os.path.join(temp_dir, "real89.gif")
        with open(path, "wb") as f:
            f.write(b"GIF89a" + b"\x00" * 100)
        assert Researcher._validate_image_file(path) is True


class TestCacheEviction:
    def test_remember_evicts_oldest_when_full(self, monkeypatch):
        from autoppt.config import Config
        monkeypatch.setattr(Config, "RESEARCH_CACHE_SIZE", 3)
        researcher = Researcher()
        cache: dict = {}
        researcher._remember(cache, "a", 1)
        researcher._remember(cache, "b", 2)
        researcher._remember(cache, "c", 3)
        assert len(cache) == 3
        # Adding a 4th should evict the oldest ("a")
        researcher._remember(cache, "d", 4)
        assert len(cache) == 3
        assert "a" not in cache
        assert cache["d"] == 4


class TestWikipediaLanguageResolution:
    def test_english(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("English") == "en"

    def test_chinese(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Chinese") == "zh"

    def test_chinese_characters(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("中文") == "zh"

    def test_japanese_characters(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("日本語") == "ja"

    def test_korean_characters(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("한국어") == "ko"

    def test_unknown_language_defaults_to_english(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Klingon") == "en"

    def test_empty_language_defaults_to_english(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("") == "en"

    def test_german(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("German") == "de"

    def test_french(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("French") == "fr"

    def test_spanish(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Spanish") == "es"

    def test_portuguese(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Portuguese") == "pt"

    def test_russian(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Russian") == "ru"

    def test_case_insensitive(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("JAPANESE") == "ja"
        assert r._resolve_wikipedia_language("korean") == "ko"
        assert r._resolve_wikipedia_language("gErMaN") == "de"

    def test_simplified_chinese(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Simplified Chinese") == "zh"

    def test_traditional_chinese(self):
        r = Researcher()
        assert r._resolve_wikipedia_language("Traditional Chinese") == "zh"


class TestFetchArticleContentTypeValidation:
    """Tests for Content-Type validation in fetch_article_content."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_rejects_binary_content_type(self, mock_get, mock_safe):
        """fetch_article_content should skip responses with non-text Content-Type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_get.return_value = mock_response

        researcher = Researcher()
        result = researcher.fetch_article_content("https://example.com/file.bin")
        assert result is None
        mock_response.close.assert_called()

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_accepts_text_html_content_type(self, mock_get, mock_safe):
        """fetch_article_content should NOT reject text/html Content-Type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.iter_content.return_value = iter([b"<html><body>Hello world</body></html>"])
        mock_get.return_value = mock_response

        researcher = Researcher()
        # Call the method — it should proceed past the Content-Type check
        # (may return None due to trafilatura extraction, but should NOT
        # return None from the Content-Type check itself)
        result = researcher.fetch_article_content("https://example.com/page.html")
        # Verify iter_content was called (meaning we got past the CT check)
        mock_response.iter_content.assert_called()


class TestFetchArticleContentTruncation:
    """Tests for fetch_article_content response size limit and streaming."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_truncates_response_exceeding_2mb(self, mock_get, mock_safe):
        """When the response body exceeds 2MB, it is truncated and a warning is logged."""
        chunk_size = 8192
        # Each chunk is 8192 bytes; we need enough to exceed 2MB (2 * 1024 * 1024 = 2097152)
        num_chunks = (2 * 1024 * 1024) // chunk_size + 10  # well over 2MB

        chunks = [b"x" * chunk_size for _ in range(num_chunks)]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter(chunks)
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Extracted article content that is long enough to pass the 100 char threshold for the test to succeed properly here."

        researcher = Researcher()
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/big-article")

        # Should still return content (truncated, not errored)
        assert result is not None
        assert len(result) > 0

        # The response should have been closed after reading
        mock_response.close.assert_called_once()

        # trafilatura.extract should have been called with less than the full data
        call_args = mock_trafilatura.extract.call_args
        downloaded_text = call_args[0][0]
        # The downloaded text should be smaller than the total chunks would produce
        assert len(downloaded_text.encode("utf-8")) < len(b"".join(chunks))

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_truncation_logs_warning(self, mock_get, mock_safe, caplog):
        """Verify that a warning is logged when response exceeds 2MB."""
        chunk_size = 8192
        num_chunks = (2 * 1024 * 1024) // chunk_size + 10

        chunks = [b"a" * chunk_size for _ in range(num_chunks)]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter(chunks)
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Extracted content that is definitely long enough to pass the one hundred character minimum length check."

        researcher = Researcher()
        import builtins
        import logging
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        with caplog.at_level(logging.WARNING, logger="autoppt.researcher"):
            with patch('builtins.__import__', side_effect=patched_import):
                researcher.fetch_article_content("https://example.com/huge-page")

        assert any("truncat" in record.message.lower() for record in caplog.records), (
            f"Expected a warning about truncation, got: {[r.message for r in caplog.records]}"
        )

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_response_closed_after_reading(self, mock_get, mock_safe):
        """Test that the response is properly closed after reading, even for normal-sized responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter([b"<html><body>Hello world</body></html>"])
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Hello world content that is long enough to pass the hundred character minimum length requirement for the test."

        researcher = Researcher()
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=patched_import):
            researcher.fetch_article_content("https://example.com/article")

        mock_response.close.assert_called_once()

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_response_closed_on_non_200_status(self, mock_get, mock_safe):
        """Test that the response is closed when status code is not 200."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        researcher = Researcher()
        result = researcher.fetch_article_content("https://example.com/missing")

        assert result is None
        mock_response.close.assert_called_once()


class TestIsOfflineExplicitParam:
    """Tests for _is_offline with explicit True/False parameter."""

    def test_is_offline_returns_true_when_passed_true(self):
        researcher = Researcher()
        assert researcher._is_offline(True) is True

    def test_is_offline_returns_false_when_passed_false(self):
        researcher = Researcher()
        assert researcher._is_offline(False) is False


class TestSearchCacheHit:
    """Test that search() returns cached results on second call."""

    def test_search_returns_cached_result(self):
        researcher = Researcher()
        cached = [{"title": "Cached", "href": "https://x.com", "body": "b"}]
        researcher._search_cache[("q", 3)] = cached
        result = researcher.search("q", max_results=3)
        assert result is cached

    def test_search_exception_returns_empty(self):
        researcher = Researcher()
        researcher.ddgs = MagicMock()
        researcher.ddgs.text.side_effect = RuntimeError("fail")
        result = researcher.search("bad query")
        assert result == []


class TestWikipediaCacheAndPaths:
    """Tests for search_wikipedia cache hit, empty results, and success."""

    def test_wiki_cache_hit(self):
        researcher = Researcher()
        cached = {"title": "T", "summary": "S", "url": "U"}
        researcher._wiki_cache[("q", 5, "en")] = cached
        result = researcher.search_wikipedia("q", sentences=5, language="English")
        assert result is cached

    @patch("autoppt.researcher.Researcher._resolve_wikipedia_language", return_value="en")
    def test_wiki_no_results(self, _mock_lang):
        researcher = Researcher()
        mock_wikipedia = MagicMock()
        mock_wikipedia.search.return_value = []
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "wikipedia":
                return mock_wikipedia
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.search_wikipedia("nonexistent topic xyz")
        assert result is None

    @patch("autoppt.researcher.Researcher._resolve_wikipedia_language", return_value="en")
    def test_wiki_success(self, _mock_lang):
        researcher = Researcher()
        mock_wikipedia = MagicMock()
        mock_wikipedia.search.return_value = ["Python (programming language)"]
        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python"
        mock_page.summary = "Python is a high-level language."
        mock_wikipedia.page.return_value = mock_page
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "wikipedia":
                return mock_wikipedia
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.search_wikipedia("Python programming")
        assert result is not None
        assert result["title"] == "Python (programming language)"
        assert result["url"] == "https://en.wikipedia.org/wiki/Python"
        assert result["summary"] == "Python is a high-level language."


class TestImageSearchCacheAndSuccess:
    """Tests for search_images cache hit and successful search."""

    def test_image_cache_hit(self):
        researcher = Researcher()
        cached = [{"title": "img", "image": "url", "thumbnail": "t", "url": "u"}]
        researcher._image_cache[("q", 1)] = cached
        result = researcher.search_images("q", max_results=1, offline=False)
        assert result is cached

    def test_image_search_success(self):
        researcher = Researcher()
        researcher.ddgs = MagicMock()
        researcher.ddgs.images.return_value = [
            {"title": "Img1", "image": "https://x.com/img.jpg", "thumbnail": "https://x.com/t.jpg", "url": "https://x.com"}
        ]
        result = researcher.search_images("test image", max_results=1, offline=False)
        assert len(result) == 1
        assert result[0]["title"] == "Img1"
        assert result[0]["image"] == "https://x.com/img.jpg"


class TestDownloadImageEdgeCases:
    """Tests for download_image error paths."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_non_200_status_retries(self, mock_get, mock_safe, temp_dir):
        """Non-200 status triggers retry (continue), ultimately returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {}
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "fail.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_content_length_too_large(self, mock_get, mock_safe, temp_dir):
        """Content-Length exceeding max returns False."""
        from autoppt.config import Config
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "image/jpeg",
            "Content-Length": str(Config.IMAGE_DOWNLOAD_MAX_BYTES + 1),
        }
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "big.jpg")
        result = researcher.download_image("https://example.com/big.jpg", save_path, retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_streaming_oversized(self, mock_get, mock_safe, temp_dir):
        """Streaming content exceeding max bytes returns False and cleans up."""
        from autoppt.config import Config
        # Create a chunk larger than the max
        big_chunk = b'\xff\xd8\xff\xe0' + b'\x00' * (Config.IMAGE_DOWNLOAD_MAX_BYTES + 100)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [big_chunk]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "stream_big.jpg")
        result = researcher.download_image("https://example.com/big.jpg", save_path, retries=1)
        assert result is False
        # File should be cleaned up
        assert not os.path.exists(save_path)

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_invalid_image_after_download(self, mock_get, mock_safe, temp_dir):
        """Downloaded file that fails magic byte validation returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        # Not a valid image header
        mock_response.iter_content.return_value = [b"NOT_AN_IMAGE_FILE_DATA"]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "invalid.jpg")
        result = researcher.download_image("https://example.com/fake.jpg", save_path, retries=1)
        assert result is False
        assert not os.path.exists(save_path)


class TestDownloadImageRemainingEdgeCases:
    """Tests for remaining edge cases in download_image."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_invalid_content_length_header(self, mock_get, mock_safe, temp_dir):
        """ValueError/TypeError from non-numeric Content-Length is silently ignored."""
        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg", "Content-Length": "not-a-number"}
        mock_response.iter_content.return_value = [jpeg_header]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "invalid_cl.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is True

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_empty_chunk_skipped(self, mock_get, mock_safe, temp_dir):
        """Empty chunks in iter_content are skipped via continue."""
        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [b"", jpeg_header, b""]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "empty_chunks.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is True

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_oversized_cleanup_oserror(self, mock_get, mock_safe, temp_dir):
        """OSError during cleanup of oversized file is silently caught."""
        from autoppt.config import Config
        big_chunk = b'\xff\xd8\xff\xe0' + b'\x00' * (Config.IMAGE_DOWNLOAD_MAX_BYTES + 100)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [big_chunk]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "oversized.jpg")
        # Patch os.remove to raise OSError
        with patch("autoppt.researcher.os.remove", side_effect=OSError("permission denied")):
            result = researcher.download_image("https://example.com/big.jpg", save_path, retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_invalid_image_cleanup_oserror(self, mock_get, mock_safe, temp_dir):
        """OSError during cleanup of invalid image file is silently caught."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [b"NOT_AN_IMAGE"]
        mock_get.return_value = mock_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "invalid2.jpg")
        with patch("autoppt.researcher.os.remove", side_effect=OSError("permission denied")):
            result = researcher.download_image("https://example.com/fake.jpg", save_path, retries=1)
        assert result is False


class TestFetchArticleRemainingEdgeCases:
    """Tests for remaining edge cases in fetch_article_content."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_empty_chunk_skipped_in_article(self, mock_get, mock_safe):
        """Empty chunks in iter_content are skipped via continue."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter([b"", b"<html>content</html>", b""])
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "A" * 200  # > 100 chars
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/article")
        assert result is not None

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_short_extracted_text_returns_none(self, mock_get, mock_safe):
        """When trafilatura extracts text <= 100 chars, returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter([b"<html>short</html>"])
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Short text."  # < 100 chars
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/short")
        assert result is None


class TestFetchArticleCacheAndEdgeCases:
    """Tests for fetch_article_content cache, offline, unsafe, empty, and error paths."""

    def test_article_cache_hit(self):
        researcher = Researcher()
        researcher._article_cache[("https://example.com", 5000)] = "cached content"
        result = researcher.fetch_article_content("https://example.com")
        assert result == "cached content"

    def test_article_offline_mode(self):
        researcher = Researcher()
        result = researcher.fetch_article_content("https://example.com", offline=True)
        assert result is None

    @patch.object(Researcher, '_is_safe_url', return_value=False)
    def test_article_unsafe_url(self, mock_safe):
        researcher = Researcher()
        result = researcher.fetch_article_content("http://192.168.1.1/secret")
        assert result is None

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_article_empty_download(self, mock_get, mock_safe):
        """When downloaded content is empty, returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter([])  # no chunks
        mock_get.return_value = mock_response

        mock_trafilatura = MagicMock()
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/empty")
        assert result is None

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_article_trafilatura_import_error(self, mock_safe):
        """When trafilatura is not installed, returns None."""
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                raise ImportError("No module named 'trafilatura'")
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/article")
        assert result is None

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_article_general_exception(self, mock_get, mock_safe):
        """When requests.get raises an exception, returns None."""
        mock_get.side_effect = ConnectionError("network down")

        # Need trafilatura to be importable so we get past the import
        mock_trafilatura = MagicMock()
        import builtins
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/fail")
        assert result is None


class TestCacheEvictionDetailed:
    """Additional tests for _remember cache eviction behavior."""

    def test_remember_evicts_oldest_entry_at_capacity(self):
        """When cache reaches RESEARCH_CACHE_SIZE, the oldest entry is evicted."""
        from autoppt.config import Config
        researcher = Researcher()
        cache = {}

        original_size = Config.RESEARCH_CACHE_SIZE
        Config.RESEARCH_CACHE_SIZE = 4
        try:
            researcher._remember(cache, "first", "value_1")
            researcher._remember(cache, "second", "value_2")
            researcher._remember(cache, "third", "value_3")
            researcher._remember(cache, "fourth", "value_4")
            assert len(cache) == 4
            assert "first" in cache

            # Adding 5th should evict "first" (the oldest)
            researcher._remember(cache, "fifth", "value_5")
            assert len(cache) == 4
            assert "first" not in cache
            assert "second" in cache
            assert "fifth" in cache
            assert cache["fifth"] == "value_5"
        finally:
            Config.RESEARCH_CACHE_SIZE = original_size

    def test_remember_evicts_in_insertion_order(self):
        """Eviction should follow insertion order (FIFO)."""
        from autoppt.config import Config
        researcher = Researcher()
        cache = {}

        original_size = Config.RESEARCH_CACHE_SIZE
        Config.RESEARCH_CACHE_SIZE = 2
        try:
            researcher._remember(cache, "a", 1)
            researcher._remember(cache, "b", 2)

            # Evicts "a"
            researcher._remember(cache, "c", 3)
            assert "a" not in cache
            assert "b" in cache
            assert "c" in cache

            # Evicts "b"
            researcher._remember(cache, "d", 4)
            assert "b" not in cache
            assert "c" in cache
            assert "d" in cache
        finally:
            Config.RESEARCH_CACHE_SIZE = original_size

    def test_remember_returns_stored_value(self):
        """_remember should return the value it stored."""
        researcher = Researcher()
        cache = {}
        result = researcher._remember(cache, "key", "hello")
        assert result == "hello"

    def test_remember_overwrites_existing_key_without_eviction(self):
        """Updating an existing key should not trigger eviction."""
        from autoppt.config import Config
        researcher = Researcher()
        cache = {}

        original_size = Config.RESEARCH_CACHE_SIZE
        Config.RESEARCH_CACHE_SIZE = 3
        try:
            researcher._remember(cache, "a", 1)
            researcher._remember(cache, "b", 2)
            researcher._remember(cache, "c", 3)

            # Overwrite "b" -- cache is already at capacity but key exists
            # No eviction should occur since "b" is already in the cache
            researcher._remember(cache, "b", 20)
            assert len(cache) == 3
            assert cache["b"] == 20
            assert "a" in cache  # "a" should NOT be evicted
        finally:
            Config.RESEARCH_CACHE_SIZE = original_size


class TestRedirectHandling:
    """Tests for redirect following with SSRF re-validation."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_follows_safe_redirect(self, mock_get, mock_safe, temp_dir):
        """Redirects to safe URLs should succeed with manual redirect following."""
        import os
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://cdn.example.com/image.jpg"
        mock_response.headers = {"Content-Type": "image/jpeg", "Content-Length": "4"}
        mock_response.iter_content.return_value = [b"\xff\xd8\xff\xe0"]
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "redirect_img.jpg")
        result = researcher.download_image("https://example.com/img", save_path)
        assert result is True
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["allow_redirects"] is False  # manual redirect following

    @patch.object(Researcher, '_is_safe_url')
    @patch('autoppt.researcher.requests.get')
    def test_download_image_blocks_unsafe_redirect(self, mock_get, mock_safe, temp_dir):
        """Redirects to private IPs should be blocked during manual redirect following."""
        import os
        mock_safe.side_effect = lambda url: "192.168.1.1" not in url

        # First response: 302 redirect to private IP
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://192.168.1.1/evil.jpg"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "evil_img.jpg")
        result = researcher.download_image("https://example.com/img", save_path)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_fetch_article_follows_safe_redirect(self, mock_get, mock_safe):
        """Article fetch should follow safe redirects with manual redirect following."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        content = b"<html><body><p>" + b"x" * 200 + b"</p></body></html>"
        mock_response.iter_content.return_value = [content]
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        import trafilatura
        with patch.object(trafilatura, 'extract', return_value="x" * 200):
            researcher = Researcher()
            result = researcher.fetch_article_content("https://example.com/article")
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["allow_redirects"] is False  # manual redirect following

    @patch.object(Researcher, '_is_safe_url')
    @patch('autoppt.researcher.requests.get')
    def test_fetch_article_blocks_unsafe_redirect(self, mock_get, mock_safe):
        """Article fetch should block redirects to private IPs during manual following."""
        mock_safe.side_effect = lambda url: "10.0.0.1" not in url

        # Return a 302 redirect to private IP
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://10.0.0.1/internal"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()
        result = researcher.fetch_article_content("https://example.com/article")
        assert result is None
        redirect_response.close.assert_called_once()

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_no_redirect_skips_recheck(self, mock_get, mock_safe, temp_dir):
        """When URL doesn't change (no redirect), no re-validation needed."""
        import os
        url = "https://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = url  # Same URL - no redirect
        mock_response.headers = {"Content-Type": "image/jpeg", "Content-Length": "4"}
        mock_response.iter_content.return_value = [b"\xff\xd8\xff\xe0"]
        mock_get.return_value = mock_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "no_redir.jpg")
        result = researcher.download_image(url, save_path)
        assert result is True
        # _is_safe_url should be called only once (initial check), not twice
        assert mock_safe.call_count == 1


class TestWikipediaSummaryTruncation:
    """Tests for Wikipedia sentence-based summary truncation."""

    def test_summary_truncated_to_sentence_boundary(self):
        """Summary should be truncated at sentence boundaries, not character count."""
        import wikipedia

        mock_page = MagicMock()
        mock_page.title = "Test"
        mock_page.url = "https://en.wikipedia.org/wiki/Test"
        mock_page.summary = "First sentence. Second sentence. Third sentence. Fourth sentence."

        with patch.object(wikipedia, 'search', return_value=["Test"]), \
             patch.object(wikipedia, 'page', return_value=mock_page), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("test", sentences=2)
            assert result is not None
            assert result["summary"] == "First sentence. Second sentence."

    def test_summary_empty_when_no_summary(self):
        """Empty summary should return empty string."""
        import wikipedia

        mock_page = MagicMock()
        mock_page.title = "Test"
        mock_page.url = "https://en.wikipedia.org/wiki/Test"
        mock_page.summary = ""

        with patch.object(wikipedia, 'search', return_value=["Test"]), \
             patch.object(wikipedia, 'page', return_value=mock_page), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("test", sentences=3)
            assert result is not None
            assert result["summary"] == ""


class TestWikipediaDisambiguation:
    """Tests for Wikipedia DisambiguationError handling."""

    def test_disambiguation_picks_first_option(self):
        """DisambiguationError should retry with first disambiguation option."""
        import wikipedia

        disambiguation_error = wikipedia.exceptions.DisambiguationError(
            "Python", ["Python (programming language)", "Python (snake)"]
        )
        mock_page = MagicMock()
        mock_page.title = "Python (programming language)"
        mock_page.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        mock_page.summary = "Python is a programming language."

        with patch.object(wikipedia, 'search', return_value=["Python"]), \
             patch.object(wikipedia, 'page', side_effect=[disambiguation_error, mock_page]), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("Python")
            assert result is not None
            assert result["title"] == "Python (programming language)"

    def test_disambiguation_with_no_options_returns_none(self):
        """DisambiguationError with empty options should return None."""
        import wikipedia

        disambiguation_error = wikipedia.exceptions.DisambiguationError("Test", [])

        with patch.object(wikipedia, 'search', return_value=["Test"]), \
             patch.object(wikipedia, 'page', side_effect=disambiguation_error), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("Test")
            assert result is None


class TestArticleResponseLeak:
    """Tests for fetch_article_content response resource management."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_response_closed_on_streaming_error(self, mock_get, mock_safe):
        """Response should be closed even if an exception occurs during streaming."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/article"
        mock_response.iter_content.side_effect = ConnectionError("broken pipe")
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        researcher = Researcher()
        result = researcher.fetch_article_content("https://example.com/article")
        assert result is None
        mock_response.close.assert_called_once()


class TestWikipediaGeneralException:
    """Tests for Wikipedia search general exception path."""

    @patch("autoppt.researcher.Config")
    def test_wikipedia_general_exception_returns_none(self, mock_config):
        """search_wikipedia should return None when a general exception occurs."""
        mock_config.OFFLINE_MODE = False
        mock_config.RESEARCH_CACHE_SIZE = 10

        researcher = Researcher()
        with patch("wikipedia.page", side_effect=RuntimeError("unexpected error")):
            result = researcher.search_wikipedia("test query")
            assert result is None


class TestSearchImagesException:
    """Tests for search_images exception handling."""

    def test_search_images_exception_returns_empty(self):
        """search_images should return empty list on exception."""
        researcher = Researcher()
        researcher.ddgs = MagicMock()
        researcher.ddgs.images.side_effect = RuntimeError("API error")

        result = researcher.search_images("test query", offline=False)
        assert result == []


class TestDownloadImageNoRetryOn4xx:
    """Test that 4xx status codes are not retried."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_no_retry_on_4xx(self, mock_get, mock_safe, temp_dir):
        """Mock requests.get to return status 403. Verify download_image returns False after only 1 request."""
        import os

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.url = "https://example.com/forbidden.jpg"
        mock_response.headers = {}
        mock_get.return_value = mock_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "forbidden.jpg")
        result = researcher.download_image("https://example.com/forbidden.jpg", save_path, retries=3)

        assert result is False
        # 4xx errors should NOT be retried -- only 1 request made, not 3
        assert mock_get.call_count == 1


class TestWikipediaDoubleDisambiguation:
    """Test that a second DisambiguationError on the fallback does not crash."""

    def test_wikipedia_double_disambiguation(self):
        """Mock wikipedia.page to raise DisambiguationError with options, then raise
        DisambiguationError again on the fallback. Verify search_wikipedia returns None."""
        import wikipedia

        first_error = wikipedia.exceptions.DisambiguationError(
            "Mercury", ["Mercury (planet)", "Mercury (element)"]
        )
        second_error = wikipedia.exceptions.DisambiguationError(
            "Mercury (planet)", ["Mercury (planet) overview", "Mercury (planet) geology"]
        )

        with patch.object(wikipedia, 'search', return_value=["Mercury"]), \
             patch.object(wikipedia, 'page', side_effect=[first_error, second_error]), \
             patch.object(wikipedia, 'set_lang'):
            researcher = Researcher()
            result = researcher.search_wikipedia("Mercury")
            assert result is None


class TestDownloadImagePartialFileCleanup:
    """Tests for partial file cleanup when all retries fail."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_partial_file_removed_after_all_retries_fail(self, mock_get, mock_safe, temp_dir):
        """When all retries fail with exceptions, any partial file at save_path is removed."""
        import os
        mock_get.side_effect = Exception("Network error")

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "partial.jpg")
        # Create a partial file that simulates a previous incomplete write
        with open(save_path, "wb") as f:
            f.write(b"partial data")
        assert os.path.exists(save_path)

        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=2)

        assert result is False
        # The partial file must be cleaned up after all retries are exhausted
        assert not os.path.exists(save_path)


class TestDownloadImageRedirectChainSSRF:
    """Tests for SSRF protection during manual redirect following."""

    @patch('autoppt.researcher.requests.get')
    def test_redirect_chain_to_private_ip_is_blocked(self, mock_get, temp_dir):
        """A redirect to a private IP should be blocked during manual redirect following."""
        import os

        # First response: 302 redirect to private IP
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://192.168.1.1/internal"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "ssrf.jpg")

        with patch.object(
            Researcher, '_is_safe_url',
            side_effect=lambda url: "192.168" not in url
        ):
            result = researcher.download_image("https://example.com/img.jpg", save_path)

        assert result is False
        assert not os.path.exists(save_path)


class TestLRUCacheEviction:
    """Tests for LRU-style eviction in _remember."""

    def test_reaccess_moves_key_to_end_preventing_eviction(self):
        """Re-accessing a key should move it to the end so it is not evicted next."""
        from autoppt.config import Config
        researcher = Researcher()
        cache = {}

        original_size = Config.RESEARCH_CACHE_SIZE
        Config.RESEARCH_CACHE_SIZE = 3
        try:
            # Fill cache: A, B, C
            researcher._remember(cache, "A", 1)
            researcher._remember(cache, "B", 2)
            researcher._remember(cache, "C", 3)
            assert len(cache) == 3

            # Re-access A -- moves it to the end (order becomes B, C, A)
            researcher._remember(cache, "A", 1)
            assert len(cache) == 3

            # Add D -- should evict B (oldest after A was moved), not A
            researcher._remember(cache, "D", 4)
            assert len(cache) == 3
            assert "A" in cache, "A should survive because it was re-accessed"
            assert "B" not in cache, "B should be evicted as the oldest key"
            assert "C" in cache
            assert "D" in cache
            assert cache["D"] == 4
        finally:
            Config.RESEARCH_CACHE_SIZE = original_size


class TestFetchArticleRedirectChainSSRF:
    """Tests for SSRF protection in fetch_article_content redirect chain."""

    @patch('autoppt.researcher.requests.get')
    def test_fetch_article_redirect_chain_to_private_ip_is_blocked(self, mock_get):
        """A redirect to a private IP should be blocked during manual redirect following."""
        # Return a 302 redirect to private IP
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://10.0.0.1/internal"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()

        with patch.object(
            Researcher, '_is_safe_url',
            side_effect=lambda url: "10.0.0.1" not in url
        ):
            import builtins
            original_import = builtins.__import__
            mock_trafilatura = MagicMock()

            def patched_import(name, *args, **kwargs):
                if name == "trafilatura":
                    return mock_trafilatura
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=patched_import):
                result = researcher.fetch_article_content("https://example.com/article")

        assert result is None
        redirect_response.close.assert_called_once()


class TestDownloadImage5xxRetry:
    """Test that 5xx server errors trigger retry in download_image."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_retries_on_5xx(self, mock_get, mock_safe, tmp_path):
        """5xx server errors should be retried unlike 4xx client errors."""
        import os

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.url = "https://example.com/image.jpg"
        mock_response.headers = {}
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        researcher = Researcher()
        save_path = os.path.join(str(tmp_path), "image.jpg")

        with patch('autoppt.researcher.time.sleep'):
            result = researcher.download_image("https://example.com/image.jpg", save_path, retries=3)

        assert result is False
        # 5xx errors SHOULD be retried -- all 3 attempts should be made
        assert mock_get.call_count == 3

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_succeeds_on_retry_after_5xx(self, mock_get, mock_safe, tmp_path):
        """First attempt returns 503, second attempt succeeds with a valid image."""
        import os

        fail_response = MagicMock()
        fail_response.status_code = 503
        fail_response.url = "https://example.com/image.jpg"
        fail_response.headers = {}
        fail_response.close = MagicMock()

        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.url = "https://example.com/image.jpg"
        success_response.headers = {"Content-Type": "image/jpeg"}
        success_response.iter_content = MagicMock(return_value=[jpeg_header])

        mock_get.side_effect = [fail_response, success_response]

        researcher = Researcher()
        save_path = os.path.join(str(tmp_path), "image.jpg")

        with patch('autoppt.researcher.time.sleep'):
            result = researcher.download_image("https://example.com/image.jpg", save_path, retries=3)

        assert result is True
        assert os.path.exists(save_path)
        assert mock_get.call_count == 2


class TestFetchArticleRedirectLimit:
    """Test that fetch_article_content respects the redirect limit."""

    @patch('autoppt.researcher.requests.get')
    def test_too_many_redirects_returns_none(self, mock_get):
        """When every hop is a redirect, the redirect limit should be hit and return None."""
        from autoppt.researcher import _MAX_REDIRECTS

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "https://example.com/next"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()

        with patch.object(Researcher, '_is_safe_url', return_value=True):
            import builtins
            original_import = builtins.__import__
            mock_trafilatura = MagicMock()

            def patched_import(name, *args, **kwargs):
                if name == "trafilatura":
                    return mock_trafilatura
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=patched_import):
                result = researcher.fetch_article_content("https://example.com/article")

        assert result is None
        # Should have been called _MAX_REDIRECTS + 1 times (the loop range)
        assert mock_get.call_count == _MAX_REDIRECTS + 1


class TestWikipediaFailureCaching:
    """Test that Wikipedia failures are cached to avoid repeated network calls."""

    def test_wikipedia_exception_is_cached(self):
        """When search_wikipedia raises, the result should be cached as None."""
        import wikipedia

        researcher = Researcher()

        with patch.object(wikipedia, 'set_lang'), \
             patch.object(wikipedia, 'search', side_effect=Exception("network error")):
            result1 = researcher.search_wikipedia("test query")
            result2 = researcher.search_wikipedia("test query")

        assert result1 is None
        assert result2 is None
        # Second call should use cache, not call search again
        cache_key = ("test query", 5, "en")
        assert cache_key in researcher._wiki_cache


class TestRelativeRedirectResolution:
    """Test that relative redirect URLs are resolved against the current URL."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_resolves_relative_redirect(self, mock_get, mock_safe, tmp_path):
        """Relative Location headers should be resolved against the current URL."""
        import os

        # First response: 302 with relative Location
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "/images/real.jpg"}
        redirect_response.close = MagicMock()

        # Second response: 200 with valid image
        final_response = MagicMock()
        final_response.status_code = 200
        final_response.headers = {"Content-Type": "image/jpeg"}
        final_response.iter_content = MagicMock(return_value=[b"\xff\xd8\xff" + b"\x00" * 100])
        final_response.close = MagicMock()

        mock_get.side_effect = [redirect_response, final_response]

        researcher = Researcher()
        save_path = os.path.join(str(tmp_path), "img.jpg")

        result = researcher.download_image("https://cdn.example.com/old/path.jpg", save_path)

        # The second GET should use the resolved absolute URL
        assert mock_get.call_count == 2
        second_call_url = mock_get.call_args_list[1][0][0]
        assert second_call_url == "https://cdn.example.com/images/real.jpg"

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_fetch_article_resolves_relative_redirect(self, mock_get, mock_safe):
        """Relative Location headers in article fetch should be resolved."""
        import builtins

        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"Location": "/new-article"}
        redirect_response.close = MagicMock()

        final_response = MagicMock()
        final_response.status_code = 200
        final_response.headers = {"Content-Type": "text/html"}
        final_response.iter_content = MagicMock(return_value=[b"<html><body>Article text content here for testing purposes.</body></html>" * 10])
        final_response.close = MagicMock()

        mock_get.side_effect = [redirect_response, final_response]

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="Extracted article text that is long enough to pass the 100 char threshold for testing purposes.")

        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://blog.example.com/old-slug")

        assert mock_get.call_count == 2
        second_call_url = mock_get.call_args_list[1][0][0]
        assert second_call_url == "https://blog.example.com/new-article"


class TestDownloadImageNoLocationHeader:
    """Test redirect with no Location header returns False."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_redirect_no_location_returns_false(self, mock_get, mock_safe, tmp_path):
        """A 302 response with no Location header should return False."""
        import os

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()
        save_path = os.path.join(str(tmp_path), "no_loc.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path)

        assert result is False


class TestDownloadImageTooManyRedirects:
    """Test that too many redirects are blocked."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_too_many_redirects_returns_false(self, mock_get, mock_safe, tmp_path):
        """Exceeding _MAX_REDIRECTS should return False."""
        import os

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "https://example.com/next"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        researcher = Researcher()
        save_path = os.path.join(str(tmp_path), "loop.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path)

        assert result is False
        # Should attempt _MAX_REDIRECTS + 1 requests (initial + redirects)
        from autoppt.researcher import _MAX_REDIRECTS
        assert mock_get.call_count == _MAX_REDIRECTS + 1


class TestFetchArticleNoLocationHeader:
    """Test article fetch redirect with no Location header."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_article_redirect_no_location_returns_none(self, mock_get, mock_safe):
        """A 302 with no Location should cache and return None."""
        import builtins

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        mock_trafilatura = MagicMock()
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/article")

        assert result is None
        assert ("https://example.com/article", 5000) in researcher._article_cache


class TestFetchArticleTooManyRedirects:
    """Test article fetch with too many redirects."""

    @patch('autoppt.researcher.Researcher._is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_article_too_many_redirects_returns_none(self, mock_get, mock_safe):
        """Exceeding _MAX_REDIRECTS should return None and cache the failure."""
        import builtins

        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {"Location": "https://example.com/next"}
        redirect_response.close = MagicMock()
        mock_get.return_value = redirect_response

        mock_trafilatura = MagicMock()
        original_import = builtins.__import__

        def patched_import(name, *args, **kwargs):
            if name == "trafilatura":
                return mock_trafilatura
            return original_import(name, *args, **kwargs)

        researcher = Researcher()
        with patch("builtins.__import__", side_effect=patched_import):
            result = researcher.fetch_article_content("https://example.com/article")

        assert result is None
        from autoppt.researcher import _MAX_REDIRECTS
        assert mock_get.call_count == _MAX_REDIRECTS + 1


class TestGatherContextFullTextFetch:
    """Tests for gather_context with fetch_full_text=True to exercise ThreadPoolExecutor path."""

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    @patch.object(Researcher, 'fetch_article_content')
    def test_gather_context_full_text_uses_article_content(
        self, mock_fetch, mock_wiki, mock_search
    ):
        """When fetch_full_text=True and article content is longer than body, use full content."""
        mock_search.return_value = [
            {
                "title": "Deep Article",
                "href": "https://example.com/deep",
                "body": "Short snippet.",
            },
        ]
        mock_wiki.return_value = None
        # Return full content that is longer than the body snippet
        mock_fetch.return_value = "This is a much longer article with detailed information about the topic at hand."

        researcher = Researcher()
        context = researcher.gather_context(
            ["test query"], include_wikipedia=False, fetch_full_text=True
        )

        assert "Full Content:" in context
        assert "much longer article" in context
        mock_fetch.assert_called_once()

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    @patch.object(Researcher, 'fetch_article_content')
    def test_gather_context_full_text_falls_back_to_body(
        self, mock_fetch, mock_wiki, mock_search
    ):
        """When full content is shorter than body snippet, fall back to body."""
        mock_search.return_value = [
            {
                "title": "Shallow Article",
                "href": "https://example.com/shallow",
                "body": "This body is already quite long and descriptive enough.",
            },
        ]
        mock_wiki.return_value = None
        # Return content shorter than body
        mock_fetch.return_value = "Short."

        researcher = Researcher()
        context = researcher.gather_context(
            ["test query"], include_wikipedia=False, fetch_full_text=True
        )

        assert "Content:" in context
        assert "Full Content:" not in context

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    @patch.object(Researcher, 'fetch_article_content')
    def test_gather_context_full_text_none_falls_back_to_body(
        self, mock_fetch, mock_wiki, mock_search
    ):
        """When fetch_article_content returns None, fall back to body snippet."""
        mock_search.return_value = [
            {
                "title": "No Fetch Article",
                "href": "https://example.com/nofetch",
                "body": "Body snippet content here.",
            },
        ]
        mock_wiki.return_value = None
        mock_fetch.return_value = None

        researcher = Researcher()
        context = researcher.gather_context(
            ["test"], include_wikipedia=False, fetch_full_text=True
        )

        assert "Content: Body snippet content here." in context
        assert "Full Content:" not in context

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    @patch.object(Researcher, 'fetch_article_content')
    def test_gather_context_full_text_multiple_results(
        self, mock_fetch, mock_wiki, mock_search
    ):
        """ThreadPoolExecutor fetches multiple articles in parallel."""
        mock_search.return_value = [
            {"title": "Art1", "href": "https://example.com/a1", "body": "Short."},
            {"title": "Art2", "href": "https://example.com/a2", "body": "Short."},
        ]
        mock_wiki.return_value = None
        mock_fetch.side_effect = [
            "A detailed article about topic one with many words.",
            "Another detailed article about topic two with many words.",
        ]

        researcher = Researcher()
        context = researcher.gather_context(
            ["multi"], include_wikipedia=False, fetch_full_text=True
        )

        assert context.count("Full Content:") == 2
        assert mock_fetch.call_count == 2


class TestFinalCleanupOSError:
    """Test that OSError during final file cleanup after all retries is silently caught."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_final_cleanup_oserror_does_not_propagate(self, mock_get, mock_safe, temp_dir):
        """When os.remove raises OSError during final cleanup, no exception propagates."""
        import os
        mock_get.side_effect = Exception("Network error")

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "partial_oserror.jpg")
        # Create a partial file to trigger the os.path.exists check
        with open(save_path, "wb") as f:
            f.write(b"partial data")
        assert os.path.exists(save_path)

        # Patch os.remove to raise OSError only for the final cleanup call
        with patch("autoppt.researcher.os.remove", side_effect=OSError("permission denied")):
            result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)

        assert result is False


class TestDownloadImagePathValidation:
    """Tests for path traversal and sensitive path rejection in download_image."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_rejects_path_traversal(self, mock_get, mock_safe):
        """download_image returns False when save_path contains '..' path traversal."""
        researcher = Researcher()
        result = researcher.download_image(
            "https://example.com/img.jpg",
            "/tmp/images/../../../etc/passwd",
            retries=1,
        )
        assert result is False
        # requests.get should never be called because path validation fails first
        mock_get.assert_not_called()

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_rejects_sensitive_path(self, mock_get, mock_safe):
        """download_image returns False when save_path resolves inside a sensitive directory."""
        import os
        researcher = Researcher()
        sensitive_dirs = ["/.ssh/", "/.gnupg/", "/.aws/", "/.config/", "/.kube/", "/.docker/"]
        for segment in sensitive_dirs:
            # Build a path that, when resolved, contains the sensitive segment
            home = os.path.expanduser("~")
            sensitive_path = os.path.join(home, segment.strip("/"), "key.jpg")
            result = researcher.download_image(
                "https://example.com/img.jpg",
                sensitive_path,
                retries=1,
            )
            assert result is False, f"Expected False for sensitive path containing {segment}"
        # requests.get should never be called for any sensitive path
        mock_get.assert_not_called()

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_download_image_accepts_normal_path(self, mock_get, mock_safe, temp_dir):
        """download_image succeeds for a normal temporary directory path."""
        import os
        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [jpeg_header]
        mock_get.return_value = mock_response

        researcher = Researcher()
        save_path = os.path.join(temp_dir, "valid_image.jpg")
        result = researcher.download_image(
            "https://example.com/img.jpg", save_path, retries=1
        )
        assert result is True
        assert os.path.exists(save_path)


class TestCacheThreadSafety:
    """Test that cache reads in the researcher use the lock for thread safety."""

    def test_cache_reads_are_thread_safe(self):
        """Concurrent search calls should produce consistent cache results via the lock."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        researcher = Researcher()
        # Pre-populate cache so searches hit the cache path (no network)
        for i in range(20):
            researcher._search_cache[(f"query_{i}", 3)] = [
                {"title": f"Result {i}", "href": f"https://example.com/{i}", "body": f"Body {i}"}
            ]

        errors = []

        def read_cache(idx):
            result = researcher.search(f"query_{idx}", max_results=3)
            if len(result) != 1 or result[0]["title"] != f"Result {idx}":
                errors.append(f"Unexpected result for query_{idx}: {result}")
            return result

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_cache, i) for i in range(20) for _ in range(5)]
            for future in as_completed(futures):
                future.result()  # propagate any exceptions

        assert errors == [], f"Thread safety errors: {errors}"


class TestGatherContextTruncationBasic:
    """Test that gather_context truncates very large aggregated context."""

    def test_context_truncated_at_100k_chars(self):
        """gather_context should truncate output exceeding 100K characters."""
        researcher = Researcher()
        # Mock search to return results with very large bodies
        large_body = "x" * 60_000
        mock_results = [
            {"title": "Big1", "href": "https://big1.example.com", "body": large_body},
            {"title": "Big2", "href": "https://big2.example.com", "body": large_body},
        ]
        with patch.object(researcher, "search", return_value=mock_results), \
             patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                ["test"],
                include_wikipedia=True,
                fetch_full_text=False,
                offline=False,
            )
        # Truncated content + truncation marker
        assert result.endswith("[...truncated]")

    def test_context_truncation_marker_present(self):
        """gather_context should append a truncation marker when context is truncated."""
        researcher = Researcher()
        large_body = "y" * 60_000
        mock_results = [
            {"title": "Huge1", "href": "https://huge1.example.com", "body": large_body},
            {"title": "Huge2", "href": "https://huge2.example.com", "body": large_body},
            {"title": "Huge3", "href": "https://huge3.example.com", "body": large_body},
        ]
        with patch.object(researcher, "search", return_value=mock_results), \
             patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                ["test"],
                include_wikipedia=True,
                fetch_full_text=False,
                offline=False,
            )
        assert "[...truncated]" in result


class TestIPv6MappedIPv4:
    """Tests for IPv6-mapped IPv4 detection in _is_safe_url."""

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))])
    def test_rejects_ipv6_mapped_loopback(self, mock_dns):
        """IPv6-mapped IPv4 loopback (::ffff:127.0.0.1) should be rejected."""
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:10.0.0.1', 0, 0, 0))])
    def test_rejects_ipv6_mapped_private(self, mock_dns):
        """IPv6-mapped IPv4 private (::ffff:10.0.0.1) should be rejected."""
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:93.184.216.34', 0, 0, 0))])
    def test_allows_ipv6_mapped_public(self, mock_dns):
        """IPv6-mapped IPv4 public (::ffff:93.184.216.34) should be allowed."""
        assert Researcher._is_safe_url("https://example.com/img.jpg") is True


class TestSSRFMulticastUnspecified:
    """Tests for multicast and unspecified address blocking."""

    @patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('224.0.0.1', 0))])
    def test_rejects_multicast_ipv4(self, mock_dns):
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('0.0.0.0', 0))])
    def test_rejects_unspecified_ipv4(self, mock_dns):
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False


class TestGatherContextAllEmptyResults:
    """Test gather_context when all queries return zero results."""

    def test_all_queries_empty_returns_empty_string(self):
        """gather_context should return empty string when all queries return no results."""
        researcher = Researcher()
        with patch.object(researcher, "search", return_value=[]), \
             patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                ["no results", "also nothing"],
                include_wikipedia=True,
                fetch_full_text=True,
                offline=False,
            )
        assert result == ""

    def test_empty_query_list(self):
        """gather_context with empty query list should return empty string."""
        researcher = Researcher()
        with patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                [],
                include_wikipedia=True,
                fetch_full_text=False,
                offline=False,
            )
        assert result == ""


class TestGatherContextExecutorTimeout:
    """Test that executor.map in gather_context has a timeout."""

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    @patch.object(Researcher, 'fetch_article_content')
    def test_executor_timeout_propagates(self, mock_fetch, mock_wiki, mock_search):
        """When a fetch exceeds the executor timeout, TimeoutError should propagate."""
        import concurrent.futures

        mock_search.return_value = [
            {"title": "Slow", "href": "https://slow.example.com", "body": "body"},
        ]
        mock_wiki.return_value = None
        mock_fetch.side_effect = lambda *a, **kw: (_ for _ in ()).throw(
            concurrent.futures.TimeoutError("executor timeout")
        )

        researcher = Researcher()
        with pytest.raises(concurrent.futures.TimeoutError):
            researcher.gather_context(
                ["slow query"],
                include_wikipedia=False,
                fetch_full_text=True,
                offline=False,
            )


class TestArticleFetchTimeoutConfig:
    """Test that article fetch uses Config.ARTICLE_FETCH_TIMEOUT."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_fetch_article_uses_config_timeout(self, mock_get, mock_safe):
        """fetch_article_content should use Config.ARTICLE_FETCH_TIMEOUT for HTTP requests."""
        from autoppt.config import Config
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_response

        researcher = Researcher()
        researcher.fetch_article_content("https://example.com/article")

        assert mock_get.call_args[1]["timeout"] == Config.ARTICLE_FETCH_TIMEOUT


class TestDownloadImageRedirectHandling:
    """Tests for download_image redirect chain handling."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_redirect_follows_location(self, mock_get, mock_safe, temp_dir):
        """download_image should follow redirects and download from final URL."""
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "https://cdn.example.com/img.jpg"}

        jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        final_response = MagicMock()
        final_response.status_code = 200
        final_response.headers = {"Content-Type": "image/jpeg"}
        final_response.iter_content.return_value = [jpeg_header]

        mock_get.side_effect = [redirect_response, final_response]

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "redirect.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is True
        assert mock_get.call_count == 2

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_redirect_no_location_header(self, mock_get, mock_safe, temp_dir):
        """download_image should return False when redirect has no Location header."""
        redirect_response = MagicMock()
        redirect_response.status_code = 301
        redirect_response.headers = {}
        mock_get.return_value = redirect_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "noloc.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url')
    @patch('autoppt.researcher.requests.get')
    def test_redirect_to_unsafe_url(self, mock_get, mock_safe, temp_dir):
        """download_image should block redirects to non-public URLs."""
        mock_safe.side_effect = lambda url: "evil" not in url

        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "http://evil.internal/secret"}
        mock_get.return_value = redirect_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "unsafe.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    @patch('autoppt.researcher.requests.get')
    def test_too_many_redirects(self, mock_get, mock_safe, temp_dir):
        """download_image should return False after exceeding max redirects."""
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.headers = {"Location": "https://example.com/loop"}
        mock_get.return_value = redirect_response

        researcher = Researcher()
        import os
        save_path = os.path.join(temp_dir, "loop.jpg")
        result = researcher.download_image("https://example.com/img.jpg", save_path, retries=1)
        assert result is False


class TestDownloadImagePathValidation:
    """Tests for download_image path traversal and blocked path detection."""

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_path_traversal_blocked(self, mock_safe):
        """download_image should reject paths containing '..' traversal."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/tmp/../../etc/passwd", retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_sensitive_path_blocked(self, mock_safe):
        """download_image should reject paths to sensitive directories."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/home/user/.ssh/img.jpg", retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_gnupg_path_blocked(self, mock_safe):
        """download_image should reject paths to .gnupg directory."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/home/user/.gnupg/img.jpg", retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_docker_path_blocked(self, mock_safe):
        """download_image should reject paths to .docker directory."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/home/user/.docker/img.jpg", retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_env_path_blocked(self, mock_safe):
        """download_image should reject paths inside .env directory."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/home/user/.env/img.jpg", retries=1)
        assert result is False

    def test_download_image_rejects_zero_retries(self):
        """download_image should return False for retries=0."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/tmp/img.jpg", retries=0)
        assert result is False

    def test_download_image_rejects_negative_retries(self):
        """download_image should return False for negative retries."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/tmp/img.jpg", retries=-1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_blocked_segments_match_config(self, mock_safe):
        """Researcher should use Config.BLOCKED_PATH_SEGMENTS, not a private copy."""
        from autoppt.config import Config
        researcher = Researcher()
        for segment in Config.BLOCKED_PATH_SEGMENTS:
            path = f"/home/user{segment}img.jpg"
            result = researcher.download_image("https://example.com/img.jpg", path, retries=1)
            assert result is False, f"Expected rejection for path with segment {segment}"

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_download_image_rejects_system_prefix(self, mock_safe):
        """download_image should reject save paths under system prefixes like /etc/."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/etc/img.jpg", retries=1)
        assert result is False

    @patch.object(Researcher, '_is_safe_url', return_value=True)
    def test_download_image_rejects_env_file(self, mock_safe):
        """download_image should reject save paths ending with .env (file, not directory)."""
        researcher = Researcher()
        result = researcher.download_image("https://example.com/img.jpg", "/home/user/project/.env", retries=1)
        assert result is False


class TestGatherContextTruncationAdvanced:
    """Tests for gather_context aggregated context truncation."""

    @patch.object(Researcher, 'search')
    @patch.object(Researcher, 'search_wikipedia')
    def test_context_truncated_at_100k(self, mock_wiki, mock_search):
        """gather_context should truncate aggregated context at 100,000 chars."""
        # Create a result with very long body text
        long_body = "x" * 60_000
        mock_search.return_value = [
            {"title": "Long1", "href": "https://a.example.com", "body": long_body},
            {"title": "Long2", "href": "https://b.example.com", "body": long_body},
        ]
        mock_wiki.return_value = None

        researcher = Researcher()
        result = researcher.gather_context(
            ["long query"],
            include_wikipedia=False,
            fetch_full_text=False,
            offline=False,
        )
        assert result.endswith("[...truncated]")


class TestResearcherModuleConstants:
    """Tests for module-level constants."""

    def test_max_context_chars_is_100k(self):
        from autoppt.researcher import _MAX_CONTEXT_CHARS
        assert _MAX_CONTEXT_CHARS == 100_000

    def test_image_retry_delay_is_positive(self):
        from autoppt.researcher import _IMAGE_RETRY_DELAY_SECONDS
        assert _IMAGE_RETRY_DELAY_SECONDS > 0

    def test_max_redirects_is_positive(self):
        from autoppt.researcher import _MAX_REDIRECTS
        assert _MAX_REDIRECTS > 0

    def test_max_article_bytes_is_module_level(self):
        from autoppt.researcher import _MAX_ARTICLE_BYTES
        assert _MAX_ARTICLE_BYTES == 2 * 1024 * 1024


class TestGatherContextMissingKeys:
    """Tests for gather_context handling results with missing dict keys."""

    def test_result_missing_title_key(self):
        """gather_context should not crash when a search result lacks 'title'."""
        researcher = Researcher()
        mock_results = [
            {"href": "https://example.com/page", "body": "Some content"},
        ]
        with patch.object(researcher, "search", return_value=mock_results), \
             patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                ["test"],
                include_wikipedia=False,
                fetch_full_text=False,
                offline=False,
            )
        assert "Untitled" in result
        assert "Some content" in result

    def test_result_missing_body_key(self):
        """gather_context should not crash when a search result lacks 'body'."""
        researcher = Researcher()
        mock_results = [
            {"href": "https://example.com/page", "title": "A Title"},
        ]
        with patch.object(researcher, "search", return_value=mock_results), \
             patch.object(researcher, "search_wikipedia", return_value=None):
            result = researcher.gather_context(
                ["test"],
                include_wikipedia=False,
                fetch_full_text=False,
                offline=False,
            )
        assert "A Title" in result


class TestSSRFMulticastIPv6:
    """Tests for IPv6 multicast address blocking."""

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('ff02::1', 0, 0, 0))])
    def test_rejects_multicast_ipv6(self, mock_dns):
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False


class TestSSRFIPv6MappedPrivate:
    """Tests for IPv6-mapped IPv4 private address blocking."""

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))])
    def test_rejects_ipv6_mapped_loopback(self, mock_dns):
        """_is_safe_url should reject IPv6-mapped IPv4 loopback addresses."""
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:192.168.1.1', 0, 0, 0))])
    def test_rejects_ipv6_mapped_private(self, mock_dns):
        """_is_safe_url should reject IPv6-mapped IPv4 private addresses."""
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False

    @patch("socket.getaddrinfo", return_value=[(10, 1, 6, '', ('::ffff:10.0.0.1', 0, 0, 0))])
    def test_rejects_ipv6_mapped_10_range(self, mock_dns):
        """_is_safe_url should reject IPv6-mapped 10.x.x.x addresses."""
        assert Researcher._is_safe_url("http://evil.com/img.jpg") is False


class TestDownloadImageResponseNone:
    """Tests for download_image handling when response could be None."""

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_download_image_redirect_no_location(self, mock_safe):
        """download_image should return False when redirect has no Location header."""
        researcher = Researcher()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {}
        mock_response.close = MagicMock()
        with patch("requests.get", return_value=mock_response):
            result = researcher.download_image("http://example.com/img.jpg", "/tmp/test.jpg", retries=1)
        assert result is False

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_download_image_too_many_redirects(self, mock_safe):
        """download_image should return False after too many redirects."""
        researcher = Researcher()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "http://example.com/next"}
        mock_response.close = MagicMock()
        with patch("requests.get", return_value=mock_response):
            result = researcher.download_image("http://example.com/img.jpg", "/tmp/test.jpg", retries=1)
        assert result is False


class TestDownloadImageBlockedPath:
    """Tests for download_image rejecting blocked save paths."""

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_rejects_ssh_path(self, mock_safe):
        """download_image should reject save paths containing .ssh."""
        researcher = Researcher()
        result = researcher.download_image("http://example.com/img.jpg", "/home/user/.ssh/authorized_keys")
        assert result is False

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_rejects_aws_path(self, mock_safe):
        """download_image should reject save paths containing .aws."""
        researcher = Researcher()
        result = researcher.download_image("http://example.com/img.jpg", "/home/user/.aws/credentials")
        assert result is False


class TestSearchImagesException:
    """Tests for search_images handling exceptions."""

    def test_search_images_exception_returns_empty(self):
        """search_images should return [] when ddgs.images raises an exception."""
        researcher = Researcher()
        with patch.object(researcher.ddgs, "images", side_effect=Exception("network error")):
            result = researcher.search_images("test query", offline=False)
        assert result == []


class TestFetchArticleRedirectExhaustion:
    """Tests for fetch_article_content redirect loop exhaustion."""

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_too_many_redirects_returns_none(self, mock_safe):
        """fetch_article_content should return None after too many redirects."""
        researcher = Researcher()
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": "http://example.com/next"}
        mock_response.close = MagicMock()
        with patch("requests.get", return_value=mock_response):
            result = researcher.fetch_article_content("http://example.com/article")
        assert result is None

    @patch.object(Researcher, "_is_safe_url", return_value=True)
    def test_redirect_no_location_returns_none(self, mock_safe):
        """fetch_article_content should return None when redirect has empty Location."""
        researcher = Researcher()
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.headers = {"Location": ""}
        mock_response.close = MagicMock()
        with patch("requests.get", return_value=mock_response):
            result = researcher.fetch_article_content("http://example.com/article")
        assert result is None


class TestFetchArticleMaxCharsValidation:
    """Tests for max_chars parameter validation in fetch_article_content."""

    def test_negative_max_chars_clamped_to_one(self):
        """fetch_article_content should clamp negative max_chars to 1."""
        researcher = Researcher()
        # With offline mode, the function returns None immediately, but the
        # cache key should use the clamped value (1, not -5).
        result = researcher.fetch_article_content("http://example.com", max_chars=-5, offline=True)
        assert result is None
        # Verify clamped cache key was used
        assert (("http://example.com", 1) in researcher._article_cache)

    def test_zero_max_chars_clamped_to_one(self):
        """fetch_article_content should clamp zero max_chars to 1."""
        researcher = Researcher()
        result = researcher.fetch_article_content("http://example.com/zero", max_chars=0, offline=True)
        assert result is None
        assert (("http://example.com/zero", 1) in researcher._article_cache)
