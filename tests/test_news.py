from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from engine.news import (
    fetch_gdelt_articles,
    format_articles_for_llm,
    MAX_ARTICLES_FOR_LLM,
)


class TestFormatArticles:
    def test_format_empty(self):
        result = format_articles_for_llm([])
        assert result == "No recent articles found."

    def test_format_strips_html(self):
        articles = [{
            "title": "Test",
            "source": "src",
            "link": "https://example.com",
            "description": "<b>bold</b> and <i>italic</i> text",
        }]
        result = format_articles_for_llm(articles)
        assert "<b>" not in result
        assert "bold" in result

    def test_format_caps_at_80(self):
        articles = [
            {"title": f"Article {i}", "source": "src", "link": "", "description": ""}
            for i in range(100)
        ]
        result = format_articles_for_llm(articles)
        # Should only have entries 1-80
        assert "80." in result
        assert "81." not in result


class TestFetchGdeltArticles:
    GDELT_RESPONSE = {
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Tech regulation tightens",
                "seendate": "20250601T120000Z",
                "domain": "example.com",
                "language": "English",
                "sourcecountry": "United States",
            },
            {
                "url": "https://example.com/article2",
                "title": "AI governance update",
                "seendate": "20250602T080000Z",
                "domain": "example2.com",
                "language": "English",
                "sourcecountry": "United States",
            },
        ]
    }

    @patch("engine.news.requests.get")
    def test_basic_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.GDELT_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        start = datetime(2025, 6, 1, tzinfo=timezone.utc)
        end = datetime(2025, 6, 30, tzinfo=timezone.utc)
        articles = fetch_gdelt_articles(["tech regulation"], start, end)

        assert len(articles) == 2
        assert articles[0]["title"] == "Tech regulation tightens"
        assert articles[0]["description"] == ""
        assert articles[0]["link"] == "https://example.com/article1"
        assert articles[0]["source"] == "example.com"
        assert articles[0]["published"] != ""

    @patch("engine.news.requests.get")
    def test_dedup_across_keywords(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.GDELT_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        start = datetime(2025, 6, 1, tzinfo=timezone.utc)
        end = datetime(2025, 6, 30, tzinfo=timezone.utc)
        # Two keywords returning same articles — should dedup
        articles = fetch_gdelt_articles(["tech regulation", "AI governance"], start, end)
        assert len(articles) == 2

    @patch("engine.news.requests.get")
    def test_skips_empty_titles(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "articles": [
                {"url": "https://x.com", "title": "", "seendate": "20250601T120000Z", "domain": "x.com"},
                {"url": "https://y.com", "title": "Valid", "seendate": "20250601T120000Z", "domain": "y.com"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        articles = fetch_gdelt_articles(
            ["test"], datetime(2025, 6, 1), datetime(2025, 6, 30)
        )
        assert len(articles) == 1
        assert articles[0]["title"] == "Valid"

    @patch("engine.news.requests.get")
    def test_caps_at_max(self, mock_get):
        many_articles = [
            {"url": f"https://x.com/{i}", "title": f"Article {i}",
             "seendate": "20250601T120000Z", "domain": "x.com"}
            for i in range(100)
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"articles": many_articles}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        articles = fetch_gdelt_articles(
            ["test"], datetime(2025, 6, 1), datetime(2025, 6, 30)
        )
        assert len(articles) == MAX_ARTICLES_FOR_LLM

    @patch("engine.news.requests.get")
    def test_handles_failed_keyword(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        articles = fetch_gdelt_articles(
            ["test"], datetime(2025, 6, 1), datetime(2025, 6, 30)
        )
        assert articles == []

    @patch("engine.news.requests.get")
    def test_handles_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"articles": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        articles = fetch_gdelt_articles(
            ["test"], datetime(2025, 6, 1), datetime(2025, 6, 30)
        )
        assert articles == []
