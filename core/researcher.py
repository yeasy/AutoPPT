try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        raise ImportError("Please install duckduckgo-search or ddgs: pip install duckduckgo-search")

import time
from typing import List, Dict

class Researcher:
    def __init__(self):
        # Suppress the rename warning if it exists in the future
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
