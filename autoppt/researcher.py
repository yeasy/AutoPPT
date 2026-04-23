from __future__ import annotations

import ipaddress
import logging
import os
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar
from urllib.parse import urljoin, urlparse

_V = TypeVar("_V")

import requests
from ddgs import DDGS

from .config import Config

logger = logging.getLogger(__name__)


_MAX_REDIRECTS = 5
_MAX_CONTEXT_CHARS = 100_000
_MAX_ARTICLE_BYTES = 2 * 1024 * 1024  # 2 MB
_IMAGE_RETRY_DELAY_SECONDS = 2


class Researcher:
    """Research module for gathering web content and images."""

    def __init__(self) -> None:
        Config.initialize()
        self.ddgs = DDGS()
        self._search_cache: dict[tuple[str, int], list[dict[str, str]]] = {}
        self._image_cache: dict[tuple[str, int], list[dict[str, str]]] = {}
        self._wiki_cache: dict[tuple[str, int, str], dict[str, str] | None] = {}
        self._article_cache: dict[tuple[str, int], str | None] = {}
        self._context_cache: dict[tuple[tuple[str, ...], bool, bool, str, bool], str] = {}
        self._cache_lock = threading.Lock()
        self._wiki_lang_lock = threading.Lock()

    def _remember(self, cache: dict, key: object, value: _V) -> _V:
        with self._cache_lock:
            if key in cache:
                cache.pop(key)
            elif cache and len(cache) >= Config.RESEARCH_CACHE_SIZE:
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
            "中文": "zh",
            "japanese": "ja",
            "日本語": "ja",
            "korean": "ko",
            "한국어": "ko",
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
            infos = socket.getaddrinfo(parsed.hostname, None, proto=socket.IPPROTO_TCP)
            for info in infos:
                addr = ipaddress.ip_address(info[4][0])
                if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
                    addr = addr.ipv4_mapped
                if (addr.is_private or addr.is_loopback or addr.is_link_local
                        or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
                    return False
        except (socket.gaierror, socket.timeout, ValueError, OSError) as exc:
            logger.debug("URL safety check failed for %s: %s", url, exc)
            return False
        return True

    _IMAGE_MAGIC_BYTES = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG\r\n\x1a\n": "PNG",
        b"GIF87a": "GIF",
        b"GIF89a": "GIF",
    }

    @staticmethod
    def _validate_image_file(path: str) -> bool:
        """Verify the downloaded file starts with known image magic bytes."""
        try:
            with open(path, "rb") as f:
                header = f.read(12)
            if not header:
                return False
            for magic in Researcher._IMAGE_MAGIC_BYTES:
                if header.startswith(magic):
                    return True
            # WEBP: RIFF....WEBP (full check to reject WAV/AVI)
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return True
            return False
        except OSError:
            return False

    def _is_offline(self, offline: bool | None = None) -> bool:
        if offline is not None:
            return offline
        return Config.is_offline_mode()

    def search(self, query: str, max_results: int = 3) -> list[dict[str, str]]:
        cache_key = (query, max_results)
        with self._cache_lock:
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

    def search_wikipedia(self, query: str, sentences: int = 5, language: str = "English") -> dict[str, str] | None:
        cache_key = (query, sentences, self._resolve_wikipedia_language(language))
        with self._cache_lock:
            if cache_key in self._wiki_cache:
                return self._wiki_cache[cache_key]

        logger.info("Searching Wikipedia for: %s", query)
        try:
            import wikipedia

            with self._wiki_lang_lock:
                wikipedia.set_lang(cache_key[2])
                search_results = wikipedia.search(query, results=1)
                if not search_results:
                    logger.warning("No Wikipedia results for '%s'", query)
                    return self._remember(self._wiki_cache, cache_key, None)
                page_title = search_results[0]
                try:
                    page = wikipedia.page(page_title, auto_suggest=False)
                except wikipedia.exceptions.DisambiguationError as exc:
                    if exc.options:
                        try:
                            page = wikipedia.page(exc.options[0], auto_suggest=False)
                        except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError):
                            return self._remember(self._wiki_cache, cache_key, None)
                    else:
                        return self._remember(self._wiki_cache, cache_key, None)
            summary = page.summary or ""
            if summary:
                all_sentences = re.split(r'(?<=[.!?])\s+', summary)
                summary = " ".join(all_sentences[:sentences])
            result = {
                "title": page.title,
                "summary": summary,
                "url": page.url,
            }
            return self._remember(self._wiki_cache, cache_key, result)
        except Exception as exc:
            logger.warning("Wikipedia search failed for '%s': %s", query, exc)
            return self._remember(self._wiki_cache, cache_key, None)

    def search_images(self, query: str, max_results: int = 1, offline: bool | None = None) -> list[dict[str, str]]:
        if self._is_offline(offline):
            logger.info("Offline mode enabled, skipping image search for: %s", query)
            return []

        cache_key = (query, max_results)
        with self._cache_lock:
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

    def download_image(self, url: str, save_path: str, retries: int = 3, offline: bool | None = None) -> bool:
        if retries < 1:
            logger.warning("Invalid retries=%d, must be >= 1", retries)
            return False
        if self._is_offline(offline):
            logger.info("Offline mode enabled, skipping image download from: %s", url)
            return False

        if not self._is_safe_url(url):
            logger.warning("Blocked image download from non-public URL: %s", url)
            return False

        resolved_save = os.path.realpath(save_path)
        if ".." in save_path.replace("\\", "/").split("/"):
            logger.warning("Path traversal detected in save_path: %s", save_path)
            return False
        for prefix in Config.BLOCKED_SYSTEM_PREFIXES:
            if resolved_save.startswith(prefix):
                logger.warning("Blocked save to system path: %s", save_path)
                return False
        if any(seg in resolved_save for seg in Config.BLOCKED_PATH_SEGMENTS):
            logger.warning("Blocked save to sensitive path: %s", save_path)
            return False

        for attempt in range(retries):
            try:
                current_url = url
                response = None
                for _hop in range(_MAX_REDIRECTS + 1):
                    response = requests.get(
                        current_url,
                        timeout=Config.IMAGE_DOWNLOAD_TIMEOUT,
                        stream=True,
                        headers={"User-Agent": "AutoPPT"},
                        allow_redirects=False,
                    )
                    if response.status_code in (301, 302, 303, 307, 308):
                        response.close()
                        raw_location = response.headers.get("Location", "")
                        if not raw_location:
                            logger.warning("Redirect with no Location header from %s", current_url)
                            return False
                        redirect_url = urljoin(current_url, raw_location)
                        if not self._is_safe_url(redirect_url):
                            logger.warning("Redirect to non-public URL blocked: %s -> %s", current_url, redirect_url)
                            return False
                        current_url = redirect_url
                        continue
                    break
                else:
                    logger.warning("Too many redirects for %s", url)
                    return False
                if response is None:
                    logger.warning("No response received for %s", url)
                    return False
                try:
                    if response.status_code != 200:
                        logger.warning("Image download returned status %s", response.status_code)
                        if 400 <= response.status_code < 500:
                            return False
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
                    with open(resolved_save, "wb") as file_handle:
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
                            os.remove(resolved_save)
                        except OSError:
                            pass
                        return False

                    if not self._validate_image_file(resolved_save):
                        logger.warning("Downloaded file is not a valid image: %s", url)
                        try:
                            os.remove(resolved_save)
                        except OSError:
                            pass
                        return False

                    logger.debug("Downloaded image to %s", resolved_save)
                    return True
                finally:
                    response.close()
            except Exception as exc:
                logger.warning("Image download attempt %s/%s failed: %s", attempt + 1, retries, exc)
                if attempt < retries - 1:
                    time.sleep(_IMAGE_RETRY_DELAY_SECONDS)
        try:
            if os.path.exists(resolved_save):
                os.remove(resolved_save)
        except OSError:
            pass
        return False

    def gather_context(
        self,
        queries: list[str],
        include_wikipedia: bool = True,
        fetch_full_text: bool = True,
        language: str = "English",
        offline: bool | None = None,
    ) -> str:
        offline_enabled = self._is_offline(offline)
        cache_key = (tuple(queries), include_wikipedia, fetch_full_text, language, offline_enabled)
        with self._cache_lock:
            if cache_key in self._context_cache:
                return self._context_cache[cache_key]

        if offline_enabled:
            logger.info("Offline mode enabled, skipping web research for %s query terms", len(queries))
            return self._remember(self._context_cache, cache_key, "")
        aggregated_chunks: list[str] = []
        seen_urls = set()

        for query in queries:
            results = self.search(query)
            full_content_by_url: dict[str, str | None] = {}

            if fetch_full_text and results:
                worker_count = max(1, min(len(results), Config.RESEARCH_FETCH_WORKERS))
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    contents = list(
                        executor.map(
                            lambda result: self.fetch_article_content(result["href"], max_chars=3000) if result.get("href") else None,
                            results,
                            timeout=Config.ARTICLE_FETCH_TIMEOUT + 10,
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
                title = result.get("title", "Untitled")
                full_content = full_content_by_url.get(href)
                if full_content and len(full_content) > len(result.get("body", "")):
                    aggregated_chunks.append(f"Source: {title} ({href})\nFull Content:\n{full_content}\n")
                    continue

                aggregated_chunks.append(f"Source: {title} ({href})\nContent: {result.get('body', '')}\n")

            if include_wikipedia:
                wiki_result = self.search_wikipedia(query, sentences=10, language=language)
                if wiki_result and wiki_result["url"] not in seen_urls:
                    aggregated_chunks.append(
                        f"Wikipedia: {wiki_result['title']} ({wiki_result['url']})\nSummary: {wiki_result['summary']}\n"
                    )
                    seen_urls.add(wiki_result["url"])

        aggregated_context = "\n".join(aggregated_chunks)
        if len(aggregated_context) > _MAX_CONTEXT_CHARS:
            logger.warning("Truncating aggregated context from %s to %s chars", len(aggregated_context), _MAX_CONTEXT_CHARS)
            aggregated_context = aggregated_context[:_MAX_CONTEXT_CHARS] + "\n[...truncated]"
        logger.info("Gathered context from %s unique sources (%s chars)", len(seen_urls), len(aggregated_context))
        return self._remember(self._context_cache, cache_key, aggregated_context)

    def fetch_article_content(self, url: str, max_chars: int = 5000, offline: bool | None = None) -> str | None:
        max_chars = max(max_chars, 1)
        cache_key = (url, max_chars)
        with self._cache_lock:
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

            current_url = url
            response = None
            for _hop in range(_MAX_REDIRECTS + 1):
                response = requests.get(
                    current_url,
                    timeout=Config.ARTICLE_FETCH_TIMEOUT,
                    headers={"User-Agent": "AutoPPT"},
                    stream=True,
                    allow_redirects=False,
                )
                if response.status_code in (301, 302, 303, 307, 308):
                    response.close()
                    raw_location = response.headers.get("Location", "")
                    if not raw_location:
                        return self._remember(self._article_cache, cache_key, None)
                    redirect_url = urljoin(current_url, raw_location)
                    if not self._is_safe_url(redirect_url):
                        logger.warning("Redirect to non-public URL blocked: %s -> %s", current_url, redirect_url)
                        return self._remember(self._article_cache, cache_key, None)
                    current_url = redirect_url
                    continue
                break
            else:
                logger.warning("Too many redirects for %s", url)
                return self._remember(self._article_cache, cache_key, None)
            if response is None:
                logger.warning("No response received for %s", url)
                return self._remember(self._article_cache, cache_key, None)
            try:
                if response.status_code != 200:
                    logger.debug("Article fetch returned status %s for %s", response.status_code, url)
                    return self._remember(self._article_cache, cache_key, None)
                raw_ct = response.headers.get("Content-Type")
                if raw_ct and isinstance(raw_ct, str):
                    content_type = raw_ct.lower()
                    if not any(ct in content_type for ct in ("text/", "application/xhtml", "application/xml")):
                        logger.debug("Skipping non-text response from %s (%s)", url, content_type)
                        return self._remember(self._article_cache, cache_key, None)
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > _MAX_ARTICLE_BYTES:
                        logger.warning("Article from %s exceeds %s bytes, truncating", url, _MAX_ARTICLE_BYTES)
                        break
                    chunks.append(chunk)
            finally:
                response.close()
            downloaded = b"".join(chunks).decode("utf-8", errors="replace")
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
