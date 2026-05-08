# src/jarvis/tools/search.py
# ============================================
# Search Tool — DuckDuckGo (no API key needed)
#
# Uses the `duckduckgo_search` library which
# wraps DuckDuckGo's HTML interface cleanly.
# Completely free, no signup, no rate limits
# for normal personal use.
#
# Install: pip install duckduckgo-search
# ============================================

from loguru import logger


class SearchTool:
    name = "search"

    def get_schemas(self) -> dict:
        return {
            "web_search": {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": (
                        "Search the web using DuckDuckGo and return the top results. "
                        "Use this when the user asks to search for something, find information, "
                        "look up facts, or get URLs for a topic."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query, e.g. 'Python async tutorial'",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of results to return (default 5, max 10)",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            "news_search": {
                "type": "function",
                "function": {
                    "name": "news_search",
                    "description": (
                        "Search for recent news articles on a topic using DuckDuckGo News. "
                        "Use this when the user asks about current events, "
                        "latest news, or recent developments."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "News search query, e.g. 'AI developments 2025'",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of news results (default 5)",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            "get_top_url": {
                "type": "function",
                "function": {
                    "name": "get_top_url",
                    "description": (
                        "Search the web and return ONLY the URL of the top result. "
                        "Use this when the user wants to open the best result for a query "
                        "in the browser."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find the best URL for",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            "search_and_summarise": {
                "type": "function",
                "function": {
                    "name": "search_and_summarise",
                    "description": (
                        "Search the web and return a combined summary of the top results. "
                        "Use this when the user wants a quick answer or overview of a topic."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What to search for and summarise",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
        }

    def _ddg(self):
        try:
            from ddgs import DDGS
            return DDGS()
        except ImportError:
            raise ImportError(
                "ddgs not installed. Run: pip install ddgs"
            )

    def web_search(self, query: str, count: int = 5) -> str:
        logger.info(f"web_search: {query} (count={count})")
        try:
            ddg = self._ddg()
            results = list(ddg.text(query, max_results=min(count, 10)))
            if not results:
                return f"No results found for: {query}"
            lines = [f"Search results for: '{query}'\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("href", "")
                desc = r.get("body", "No description")
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                lines.append(f"{i}. {title}")
                lines.append(f"   URL: {url}")
                lines.append(f"   {desc}\n")
            return "\n".join(lines)
        except ImportError as e:
            return str(e)
        except Exception as e:
            logger.error(f"web_search failed: {e}")
            return f"Search failed: {e}"

    def news_search(self, query: str, count: int = 5) -> str:
        logger.info(f"news_search: {query}")
        try:
            ddg = self._ddg()
            results = list(ddg.news(query, max_results=min(count, 10)))
            if not results:
                return f"No news found for: {query}"
            lines = [f"Latest news for: '{query}'\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                desc = r.get("body", "")
                date = r.get("date", "")
                source = r.get("source", "")
                lines.append(f"{i}. {title}")
                if source or date:
                    lines.append(f"   {source} {date}".strip())
                lines.append(f"   URL: {url}")
                if desc:
                    lines.append(f"   {desc[:200]}\n")
            return "\n".join(lines)
        except ImportError as e:
            return str(e)
        except Exception as e:
            logger.error(f"news_search failed: {e}")
            return f"News search failed: {e}"

    def get_top_url(self, query: str) -> str:
        logger.info(f"get_top_url: {query}")
        try:
            ddg = self._ddg()
            results = list(ddg.text(query, max_results=1))
            if not results:
                return f"No results found for: {query}"
            r = results[0]
            title = r.get("title", "")
            url = r.get("href", "")
            return f"Top result: {title}\nURL: {url}"
        except ImportError as e:
            return str(e)
        except Exception as e:
            logger.error(f"get_top_url failed: {e}")
            return f"Search failed: {e}"

    def search_and_summarise(self, query: str) -> str:
        logger.info(f"search_and_summarise: {query}")
        try:
            ddg = self._ddg()
            results = list(ddg.text(query, max_results=5))
            if not results:
                return f"No results found for: {query}"
            snippets = []
            urls = []
            for r in results:
                body = r.get("body", "").strip()
                url = r.get("href", "")
                if body:
                    snippets.append(body)
                if url:
                    urls.append(url)
            combined = " ".join(snippets)
            if len(combined) > 3000:
                combined = combined[:3000] + "..."
            output = f"Summary for '{query}':\n\n{combined}\n\n"
            output += "Sources:\n" + "\n".join(f"  - {u}" for u in urls[:5])
            return output
        except ImportError as e:
            return str(e)
        except Exception as e:
            logger.error(f"search_and_summarise failed: {e}")
            return f"Search failed: {e}"