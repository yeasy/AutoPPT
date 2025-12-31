import logging
import time
from typing import List, Dict, Optional

import requests
from ddgs import DDGS

from config import Config
from .exceptions import ResearchError

logger = logging.getLogger(__name__)


class Researcher:
    """Research module for gathering web content and images."""
    
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Perform a web search and return a list of results.
        Each result contains 'title', 'href', and 'body'.
        """
        logger.info(f"Searching for: {query}")
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            clean_results = []
            for r in results:
                clean_results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
            logger.debug(f"Found {len(clean_results)} results for '{query}'")
            return clean_results
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []

    def search_wikipedia(self, query: str, sentences: int = 5) -> Optional[Dict[str, str]]:
        """
        Search Wikipedia for a topic and return a summary.
        Returns a dict with 'title', 'summary', and 'url'.
        """
        logger.info(f"Searching Wikipedia for: {query}")
        try:
            import wikipedia
            wikipedia.set_lang("en")
            
            # Search for the most relevant page
            search_results = wikipedia.search(query, results=1)
            if not search_results:
                logger.warning(f"No Wikipedia results for '{query}'")
                return None
            
            page_title = search_results[0]
            page = wikipedia.page(page_title, auto_suggest=False)
            summary = wikipedia.summary(page_title, sentences=sentences)
            
            return {
                "title": page.title,
                "summary": summary,
                "url": page.url
            }
        except Exception as e:
            logger.warning(f"Wikipedia search failed for '{query}': {e}")
            return None

    def search_images(self, query: str, max_results: int = 1) -> List[Dict[str, str]]:
        """
        Perform a web search for images and return a list of results.
        """
        logger.info(f"Searching images for: {query}")
        try:
            results = list(self.ddgs.images(query, max_results=max_results))
            clean_results = []
            for r in results:
                clean_results.append({
                    "title": r.get("title", ""),
                    "image": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", ""),
                    "url": r.get("url", "")
                })
            return clean_results
        except Exception as e:
            logger.error(f"Error searching images for '{query}': {e}")
            return []

    def download_image(self, url: str, save_path: str, retries: int = 3) -> bool:
        """
        Download an image from a URL and save it to the specified path.
        Includes retry logic for improved stability.
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=Config.IMAGE_DOWNLOAD_TIMEOUT)
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    logger.debug(f"Downloaded image to {save_path}")
                    return True
                else:
                    logger.warning(f"Image download returned status {response.status_code}")
            except Exception as e:
                logger.warning(f"Image download attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        return False

    def gather_context(self, queries: List[str], include_wikipedia: bool = True) -> str:
        """
        Run multiple queries and aggregate the results into a single context string.
        Combines DuckDuckGo web search with Wikipedia for richer content.
        Returns a formatted string suitable for LLM context.
        """
        aggregated_context = ""
        seen_urls = set()
        
        for q in queries:
            # Web search results
            results = self.search(q)
            for r in results:
                if r['href'] not in seen_urls:
                    aggregated_context += f"Source: {r['title']} ({r['href']})\nContent: {r['body']}\n\n"
                    seen_urls.add(r['href'])
            
            # Wikipedia enhancement
            if include_wikipedia:
                wiki_result = self.search_wikipedia(q)
                if wiki_result and wiki_result['url'] not in seen_urls:
                    aggregated_context += f"Wikipedia: {wiki_result['title']} ({wiki_result['url']})\nSummary: {wiki_result['summary']}\n\n"
                    seen_urls.add(wiki_result['url'])
        
        logger.info(f"Gathered context from {len(seen_urls)} unique sources")
        return aggregated_context

