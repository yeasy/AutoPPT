import ipaddress
import logging
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

_V = TypeVar("_V")

import requests  # type: ignore[import-untyped]
from ddgs import DDGS

from .config import Config

logger = logging.getLogger(__name__)


class Researcher:
    """Research module for gathering web content and images."""

    def __init__(self):
        Config.initialize()
        self.ddgs = DDGS()
        self._search_cache: Dict[Tuple[str, int], List[Dict[str, str]]] = {}
        self._image_cache: Dict[Tuple[str, int], List[Dict[str, str]]] = {}
        self._wiki_cache: Dict[Tuple[str, int, str], Optional[Dict[str, str]]] = {}
        self._article_cache: Dict[Tuple[str, int], Optional[str]] = {}
        self._context_cache: Dict[Tuple[Tuple[str, ...], bool, bool, str, bool], str] = {}

    def _remember(self, cache: Dict, key: object, value: _V) -> _V:
        if len(cache) >= Config.RESEARCH_CACHE_SIZE:
            oldest_key = next(iter(cache))
            cache.pop(oldest_key, None)
        cache[key] = value
        return value

    def _resolve_wikipedia_language(self, language: str) -> str:
        if not language:
            return "en"
        normalized = language.lower()
        mapping = {
            "english": "en",
            "chinese": "zh",
            "simplified chinese": "zh",
            "traditional chinese": "zh",
            "japanese": "ja",
            "korean": "ko",
            "french": "fr",
            "german": "de",
            "spanish": "es",
            "portuguese": "pt",
            "russian": "ru",
        }
        return mapping.get(normalized, "en")

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Reject URLs that target private/reserved IP ranges (SSRF protection)."""
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
                return False
            for info in socket.getaddrinfo(parsed.hostname, None):
                addr = ipaddress.ip_address(info[4][0])
                if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                    return False
        except (socket.gaierror, ValueError, OSError) as exc:
            logger.debug("URL safety check failed for %s: %s", url, exc)
            return False
        return True

    def _is_offline(self, offline: Optional[bool] = None) -> bool:
        if offline is not None:
            return offline
        env_offline = os.getenv("AUTOPPT_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}
        return env_offline or Config.is_offline_mode()

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        cache_key = (query, max_results)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        logger.info("Searching for: %s", query)
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            clean_results = [
                {
                    "title": result.get("title", ""),
                    "href": result.get("href", ""),
                    "body": result.get("body", ""),
                }
                for result in results
            ]
            logger.debug("Found %s results for '%s'", len(clean_results), query)
            return self._remember(self._search_cache, cache_key, clean_results)
        except Exception as exc:
            logger.error("Error searching for '%s': %s", query, exc)
            return []

    def search_wikipedia(self, query: str, sentences: int = 5, language: str = "English") -> Optional[Dict[str, str]]:
        cache_key = (query, sentences, self._resolve_wikipedia_language(language))
        if cache_key in self._wiki_cache:
            return self._wiki_cache[cache_key]

        logger.info("Searching Wikipedia for: %s", query)
        try:
            import wikipedia

            wikipedia.set_lang(cache_key[2])
            search_results = wikipedia.search(query, results=1)
            if not search_results:
                logger.warning("No Wikipedia results for '%s'", query)
                return self._remember(self._wiki_cache, cache_key, None)
            page_title = search_results[0]
            page = wikipedia.page(page_title, auto_suggest=False)
            summary = wikipedia.summary(page_title, sentences=sentences)
            result = {
                "title": page.title,
                "summary": summary,
                "url": page.url,
            }
            return self._remember(self._wiki_cache, cache_key, result)
        except Exception as exc:
            logger.warning("Wikipedia search failed for '%s': %s", query, exc)
            return None

    def search_images(self, query: str, max_results: int = 1, offline: Optional[bool] = None) -> List[Dict[str, str]]:
        if self._is_offline(offline):
            logger.info("Offline mode enabled, skipping image search for: %s", query)
            return []

        cache_key = (query, max_results)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        logger.info("Searching images for: %s", query)
        try:
            results = list(self.ddgs.images(query, max_results=max_results))
            clean_results = [
                {
                    "title": result.get("title", ""),
                    "image": result.get("image", ""),
                    "thumbnail": result.get("thumbnail", ""),
                    "url": result.get("url", ""),
                }
                for result in results
            ]
            return self._remember(self._image_cache, cache_key, clean_results)
        except Exception as exc:
            logger.error("Error searching images for '%s': %s", query, exc)
            return []

    def download_image(self, url: str, save_path: str, retries: int = 3, offline: Optional[bool] = None) -> bool:
        if self._is_offline(offline):
            logger.info("Offline mode enabled, skipping image download from: %s", url)
            return False

        if not self._is_safe_url(url):
            logger.warning("Blocked image download from non-public URL: %s", url)
            return False

        for attempt in range(retries):
            try:
                response = requests.get(
                    url,
                    timeout=Config.IMAGE_DOWNLOAD_TIMEOUT,
                    stream=True,
                    headers={"User-Agent": "AutoPPT/0.5"},
                    allow_redirects=False,
                )
                try:
                    if response.status_code != 200:
                        logger.warning("Image download returned status %s", response.status_code)
                        continue

                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type and not content_type.startswith("image/"):
                        logger.warning("Skipping non-image response from %s (%s)", url, content_type)
                        return False

                    content_length = response.headers.get("Content-Length")
                    try:
                        if content_length and int(content_length) > Config.IMAGE_DOWNLOAD_MAX_BYTES:
                            logger.warning("Skipping oversized image from %s", url)
                            return False
                    except (ValueError, TypeError):
                        pass

                    total_bytes = 0
                    oversized = False
                    with open(save_path, "wb") as file_handle:
                        for chunk in response.iter_content(chunk_size=8192):
                            if not chunk:
                                continue
                            total_bytes += len(chunk)
                            if total_bytes > Config.IMAGE_DOWNLOAD_MAX_BYTES:
                                logger.warning("Skipping image larger than %s bytes from %s", Config.IMAGE_DOWNLOAD_MAX_BYTES, url)
                                oversized = True
                                break
                            file_handle.write(chunk)
                    if oversized:
                        try:
                            os.remove(save_path)
                        except OSError:
                            pass
                        return False

                    logger.debug("Downloaded image to %s", save_path)
                    return True
                finally:
                    response.close()
            except Exception as exc:
                logger.warning("Image download attempt %s/%s failed: %s", attempt + 1, retries, exc)
                if attempt < retries - 1:
                    time.sleep(2)
        return False

    def gather_context(
        self,
        queries: List[str],
        include_wikipedia: bool = True,
        fetch_full_text: bool = True,
        language: str = "English",
        offline: Optional[bool] = None,
    ) -> str:
        offline_enabled = self._is_offline(offline)
        cache_key = (tuple(queries), include_wikipedia, fetch_full_text, language, offline_enabled)
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        if offline_enabled:
            logger.info("Offline mode enabled, skipping web research for %s query terms", len(queries))
            return self._remember(self._context_cache, cache_key, "")
        aggregated_chunks: List[str] = []
        seen_urls = set()

        for query in queries:
            results = self.search(query)
            full_content_by_url: Dict[str, Optional[str]] = {}

            if fetch_full_text and results:
                worker_count = max(1, min(len(results), Config.RESEARCH_FETCH_WORKERS))
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    contents = list(
                        executor.map(
                            lambda result: self.fetch_article_content(result["href"], max_chars=3000) if result.get("href") else None,
                            results,
                        )
                    )
                full_content_by_url = {
                    result["href"]: content
                    for result, content in zip(results, contents)
                    if result.get("href")
                }

            for result in results:
                href = result.get("href", "")
                if not href or href in seen_urls:
                    continue

                seen_urls.add(href)
                full_content = full_content_by_url.get(href)
                if full_content and len(full_content) > len(result.get("body", "")):
                    aggregated_chunks.append(f"Source: {result['title']} ({href})\nFull Content:\n{full_content}\n")
                    continue

                aggregated_chunks.append(f"Source: {result['title']} ({href})\nContent: {result['body']}\n")

            if include_wikipedia:
                wiki_result = self.search_wikipedia(query, sentences=10, language=language)
                if wiki_result and wiki_result["url"] not in seen_urls:
                    aggregated_chunks.append(
                        f"Wikipedia: {wiki_result['title']} ({wiki_result['url']})\nSummary: {wiki_result['summary']}\n"
                    )
                    seen_urls.add(wiki_result["url"])

        aggregated_context = "\n".join(aggregated_chunks)
        logger.info("Gathered context from %s unique sources (%s chars)", len(seen_urls), len(aggregated_context))
        return self._remember(self._context_cache, cache_key, aggregated_context)

    def fetch_article_content(self, url: str, max_chars: int = 5000, offline: Optional[bool] = None) -> Optional[str]:
        cache_key = (url, max_chars)
        if cache_key in self._article_cache:
            return self._article_cache[cache_key]

        if self._is_offline(offline):
            logger.info("Offline mode enabled, skipping article fetch for: %s", url)
            return self._remember(self._article_cache, cache_key, None)
        if not self._is_safe_url(url):
            logger.warning("Blocked article fetch from non-public URL: %s", url)
            return self._remember(self._article_cache, cache_key, None)
        try:
            import trafilatura

            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.debug("Could not download: %s", url)
                return self._remember(self._article_cache, cache_key, None)
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )

            if text and len(text) > 100:
                logger.debug("Extracted %s chars from %s", len(text), url)
                return self._remember(self._article_cache, cache_key, text[:max_chars])
            return self._remember(self._article_cache, cache_key, None)
        except ImportError:
            logger.warning("trafilatura not installed. Install with: pip install trafilatura")
            return self._remember(self._article_cache, cache_key, None)
        except Exception as exc:
            logger.debug("Article extraction failed for %s: %s", url, exc)
            return self._remember(self._article_cache, cache_key, None)
