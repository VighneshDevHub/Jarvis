# tests/test_search.py
# ============================================
# Unit tests for Phase 2 — Search Tool
# Run with: python -m pytest tests/test_search.py -v
# ============================================

import pytest
from unittest.mock import patch, MagicMock
from src.jarvis.tools.search import SearchTool


@pytest.fixture
def tool():
    return SearchTool()


# Mock result that ddgs returns
MOCK_RESULTS = [
    {
        "title": "Python Tutorial - W3Schools",
        "href": "https://www.w3schools.com/python/",
        "body": "Python is a popular programming language.",
    },
    {
        "title": "Python.org",
        "href": "https://www.python.org/",
        "body": "The official Python website.",
    },
    {
        "title": "Real Python",
        "href": "https://realpython.com/",
        "body": "Python tutorials for all skill levels.",
    },
]

MOCK_NEWS = [
    {
        "title": "AI news today",
        "url": "https://example.com/ai-news",
        "body": "Latest AI developments.",
        "date": "2025-01-01",
        "source": "TechNews",
    }
]


# ── web_search ───────────────────────────────

@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_web_search_returns_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = MOCK_RESULTS
    mock_ddg.return_value = mock_instance

    result = tool.web_search("Python tutorial")
    assert "W3Schools" in result
    assert "https://www.w3schools.com" in result
    assert "Python tutorial" in result


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_web_search_no_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddg.return_value = mock_instance

    result = tool.web_search("xyznonexistentquery123")
    assert "no results" in result.lower()


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_web_search_count_respected(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = MOCK_RESULTS
    mock_ddg.return_value = mock_instance

    result = tool.web_search("Python", count=2)
    mock_instance.text.assert_called_with("Python", max_results=2)


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_web_search_truncates_long_description(mock_ddg, tool):
    long_result = [{
        "title": "Test",
        "href": "https://example.com",
        "body": "x" * 500,
    }]
    mock_instance = MagicMock()
    mock_instance.text.return_value = long_result
    mock_ddg.return_value = mock_instance

    result = tool.web_search("test")
    # Description should be truncated to 200 chars + "..."
    assert "..." in result


# ── news_search ──────────────────────────────

@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_news_search_returns_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.news.return_value = MOCK_NEWS
    mock_ddg.return_value = mock_instance

    result = tool.news_search("artificial intelligence")
    assert "AI news today" in result
    assert "TechNews" in result


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_news_search_no_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.news.return_value = []
    mock_ddg.return_value = mock_instance

    result = tool.news_search("nothing")
    assert "no news" in result.lower()


# ── get_top_url ──────────────────────────────

@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_get_top_url_returns_url(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = [MOCK_RESULTS[0]]
    mock_ddg.return_value = mock_instance

    result = tool.get_top_url("Python tutorial")
    assert "https://www.w3schools.com" in result
    assert "W3Schools" in result


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_get_top_url_no_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddg.return_value = mock_instance

    result = tool.get_top_url("xyznonexistent")
    assert "no results" in result.lower()


# ── search_and_summarise ─────────────────────

@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_search_and_summarise_combines_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = MOCK_RESULTS
    mock_ddg.return_value = mock_instance

    result = tool.search_and_summarise("Python")
    assert "Python" in result
    assert "Sources:" in result
    assert "https://" in result


@patch("src.jarvis.tools.search.SearchTool._ddg")
def test_search_and_summarise_no_results(mock_ddg, tool):
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddg.return_value = mock_instance

    result = tool.search_and_summarise("nothing")
    assert "no results" in result.lower()
