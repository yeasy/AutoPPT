from ddgs import DDGS
import time
from typing import List, Dict

class Researcher:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Perform a web search and return a list of results.
        Each result contains 'title', 'href', and 'body'.
        """
        print(f"Searching for: {query}")
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            clean_results = []
            for r in results:
                clean_results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
            return clean_results
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            return []

    def search_images(self, query: str, max_results: int = 1) -> List[Dict[str, str]]:
        """
        Perform a web search for images and return a list of results.
        """
        print(f"Searching images for: {query}")
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
            print(f"Error searching images for '{query}': {e}")
            return []

    def download_image(self, url: str, save_path: str) -> bool:
        """
        Download an image from a URL and save it to the specified path.
        """
        import requests
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
            return False

    def gather_context(self, queries: List[str]) -> str:
        """
        Run multiple queries and aggregate the results into a single context string.
        Returns a formatted string suitable for LLM context.
        """
        aggregated_context = ""
        seen_urls = set()
        
        for q in queries:
            results = self.search(q)
            for r in results:
                if r['href'] not in seen_urls:
                    aggregated_context += f"Source: {r['title']} ({r['href']})\nContent: {r['body']}\n\n"
                    seen_urls.add(r['href'])
        
        return aggregated_context
