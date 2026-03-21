from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from engine.news import _parse_date, fetch_articles, format_articles_for_llm, format_feed_source


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


class TestFormatFeedSource:
    def test_google_news_with_query(self):
        url = "https://news.google.com/rss/search?q=big+tech&hl=en"
        assert format_feed_source(url) == "Google News: big tech"

    def test_google_news_no_query(self):
        url = "https://news.google.com/rss/topics/headlines"
        assert format_feed_source(url) == "Google News"

    def test_reddit(self):
        url = "https://www.reddit.com/r/technology/.rss"
        assert format_feed_source(url) == "Reddit: r/technology"

    def test_hackernews_with_query(self):
        url = "https://hnrss.org/newest?q=AI+governance"
        assert format_feed_source(url) == "HackerNews: AI governance"

    def test_hackernews_no_query(self):
        url = "https://hnrss.org/newest"
        assert format_feed_source(url) == "HackerNews"

    def test_arxiv(self):
        url = "https://export.arxiv.org/rss/cs.CY"
        assert format_feed_source(url) == "arXiv: cs.CY"

    def test_generic_domain(self):
        url = "https://feeds.reuters.com/technology"
        result = format_feed_source(url)
        assert result == "feeds.reuters.com"

    def test_malformed_url(self):
        url = "not a url at all %%"
        result = format_feed_source(url)
        assert isinstance(result, str)


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
            feeds=feeds,
            detection_prompt="",
        )

    @patch("engine.news.feedparser.parse")
    def test_fetch_dedup(self, mock_parse):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        entry1 = _make_feed_entry("Same Title", pub_date=recent)
        entry2 = _make_feed_entry("Same Title", pub_date=recent)
        mock_parse.return_value = _mock_feedparser([entry1, entry2])

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

    @patch("engine.news.feedparser.parse")
    def test_fetch_skips_empty_title(self, mock_parse):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        good = _make_feed_entry("Real Title", pub_date=recent)
        empty = _make_feed_entry("", pub_date=recent)
        mock_parse.return_value = _mock_feedparser([empty, good])

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        assert len(articles) == 1
        assert articles[0]["title"] == "Real Title"

    @patch("engine.news.feedparser.parse")
    def test_fetch_skips_no_date(self, mock_parse):
        entry = _make_feed_entry("No Date Article", pub_date=None)
        mock_parse.return_value = _mock_feedparser([entry])

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        assert len(articles) == 0

    @patch("engine.news.feedparser.parse")
    def test_fetch_respects_max_entries_per_feed(self, mock_parse):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        entries = [_make_feed_entry(f"Article {i}", pub_date=recent) for i in range(50)]
        mock_parse.return_value = _mock_feedparser(entries)

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        # MAX_ENTRIES_PER_FEED = 40, so at most 40 articles
        assert len(articles) <= 40

    @patch("engine.news.feedparser.parse")
    def test_fetch_empty_feed(self, mock_parse):
        mock_parse.return_value = _mock_feedparser([])

        config = self._make_config(["https://feed1.com/rss"])
        articles = fetch_articles(config, days=7)
        assert articles == []
