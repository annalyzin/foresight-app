from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from engine.news import _parse_date, fetch_articles, format_articles_for_llm


class TestParseDate:
    def test_published_parsed(self):
        ts = datetime(2026, 3, 15, 12, 0, 0)
        time_struct = time.localtime(ts.timestamp())
        entry = SimpleNamespace(published_parsed=time_struct)
        result = _parse_date(entry)
        assert result is not None
        assert result.year == 2026
        assert result.month == 3

    def test_updated_parsed_fallback(self):
        ts = datetime(2026, 3, 10, 8, 0, 0)
        time_struct = time.localtime(ts.timestamp())
        entry = SimpleNamespace(updated_parsed=time_struct)
        result = _parse_date(entry)
        assert result is not None
        assert result.year == 2026

    def test_no_date_returns_none(self):
        entry = SimpleNamespace()
        result = _parse_date(entry)
        assert result is None


def _make_feed_entry(title, summary="desc", link="https://example.com", pub_date=None):
    """Create a mock feedparser entry."""
    entry = {
        "title": title,
        "summary": summary,
        "link": link,
    }
    obj = SimpleNamespace(**entry)
    obj.get = entry.get
    if pub_date:
        obj.published_parsed = time.localtime(pub_date.timestamp())
    else:
        obj.published_parsed = None
    return obj


def _mock_feedparser(entries):
    """Create a mock feedparser.parse return value."""
    feed = MagicMock()
    feed.entries = entries
    return feed


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


class TestFetchArticles:
    def _make_config(self, feeds):
        from config.base import DomainConfig
        return DomainConfig(
            name="Test",
            persona="Test",
            description="Test",
            categories=["Cat"],
            key_actors=[],
            feeds=feeds,
            detection_prompt="",
        )

    @patch("engine.news.feedparser.parse")
    def test_fetch_dedup(self, mock_parse):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        entry = _make_feed_entry("Same Title", pub_date=recent)
        mock_parse.return_value = _mock_feedparser([entry, entry])

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        assert len(articles) == 1

    @patch("engine.news.feedparser.parse")
    def test_fetch_date_filter(self, mock_parse):
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        entry = _make_feed_entry("Old Article", pub_date=old_date)
        mock_parse.return_value = _mock_feedparser([entry])

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        assert len(articles) == 0

    @patch("engine.news.feedparser.parse")
    def test_fetch_skips_failed_feed(self, mock_parse):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        good_entry = _make_feed_entry("Good Article", pub_date=recent)

        def side_effect(url):
            if "bad" in url:
                raise Exception("Feed failed")
            return _mock_feedparser([good_entry])

        mock_parse.side_effect = side_effect

        config = self._make_config(["https://bad.com/rss", "https://good.com/rss"])
        articles = fetch_articles(config, days=7)
        assert len(articles) == 1
        assert articles[0]["title"] == "Good Article"
