from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.base import DomainConfig
from data.models import Signal
from engine.scanner import _parse_signals, detect_signals


@pytest.fixture
def config():
    return DomainConfig(
        name="Test Domain",
        persona="Analyst",
        description="Test",
        categories=["Antitrust", "Privacy", "AI Governance"],
        feeds=["https://feed1.com/rss", "https://feed2.com/rss"],
        detection_prompt="Categories: {categories}\nTopics: {existing_topics}\nArticles:\n{articles}",
    )


class TestParseSignals:
    def test_parse_list(self, config):
        data = [
            {"topic": "AI rules", "title": "New AI rules", "description": "desc",
             "categories": ["AI Governance"], "sources": ["Reuters"]},
        ]
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].topic == "AI rules"
        assert signals[0].domain == "Test Domain"

    def test_parse_dict_with_signals_key(self, config):
        data = {"signals": [
            {"topic": "Privacy push", "title": "GDPR update", "description": "d",
             "categories": ["Privacy"]},
        ]}
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].topic == "Privacy push"

    def test_category_validation_fallback(self, config):
        data = [
            {"topic": "t", "title": "t", "description": "d",
             "categories": ["Nonexistent Category"]},
        ]
        signals = _parse_signals(data, config)
        # Invalid category filtered out, falls back to first config category
        assert signals[0].categories == ["Antitrust"]

    def test_related_articles(self, config):
        data = [
            {"topic": "t", "title": "t", "description": "d",
             "categories": ["Privacy"],
             "related_articles": [
                 {"title": "RA1", "url": "https://example.com", "source": "Reuters"},
                 {"title": "RA2", "url": "https://example2.com", "source": "BBC"},
             ]},
        ]
        signals = _parse_signals(data, config)
        assert len(signals[0].source_articles) == 2
        assert signals[0].source_articles[0].title == "RA1"
        assert signals[0].source_articles[1].source == "BBC"

    def test_empty_categories_returns_empty(self):
        empty_config = DomainConfig(
            name="Test", persona="A", description="T",
            categories=[], feeds=[], detection_prompt="",
        )
        result = _parse_signals([{"topic": "t", "title": "t"}], empty_config)
        assert result == []

    def test_missing_fields_use_defaults(self, config):
        data = [{"description": "only desc"}]
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].topic == ""
        assert signals[0].title == "Untitled Signal"

    def test_singular_category_fallback(self, config):
        data = [{"topic": "t", "title": "t", "description": "d",
                 "category": "Privacy"}]
        signals = _parse_signals(data, config)
        assert signals[0].categories == ["Privacy"]


class TestDetectSignals:
    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.fetch_articles")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_pipeline(self, mock_topics, mock_fetch, mock_chat, config):
        mock_fetch.return_value = [
            {"title": "Test", "source": "src", "link": "", "description": "", "published": ""},
        ]
        mock_chat.return_value = [
            {"topic": "AI rules", "title": "New AI rules", "description": "d",
             "categories": ["AI Governance"], "sources": ["Reuters"]},
        ]
        signals = detect_signals(config)
        assert len(signals) >= 1
        assert all(isinstance(s, Signal) for s in signals)
        mock_fetch.assert_called_once_with(config)

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.fetch_articles")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_batch_failure_continues(self, mock_topics, mock_fetch, mock_chat, config):
        mock_fetch.return_value = [
            {"title": "Test", "source": "src", "link": "", "description": "", "published": ""},
        ]
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM failed")
            return [
                {"topic": "t", "title": "t", "description": "d",
                 "categories": ["Privacy"]},
            ]

        mock_chat.side_effect = side_effect

        with patch("engine.scanner.st", create=True):
            signals = detect_signals(config)
        # First batch fails, but other batches succeed
        assert len(signals) >= 1

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.fetch_articles")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_callbacks_invoked(self, mock_topics, mock_fetch, mock_chat, config):
        mock_fetch.return_value = [
            {"title": "T", "source": "s", "link": "", "description": "", "published": ""},
        ]
        mock_chat.return_value = [
            {"topic": "t", "title": "t", "description": "d", "categories": ["Privacy"]},
        ]
        on_start = MagicMock()
        on_end = MagicMock()
        detect_signals(config, on_batch_start=on_start, on_batch_end=on_end)
        assert on_start.call_count == len(config.categories)
        assert on_end.call_count == len(config.categories)
        # First call should be (0, total_batches, [first_category])
        first_start_args = on_start.call_args_list[0][0]
        assert first_start_args[0] == 0
        assert first_start_args[1] == len(config.categories)

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_pre_fetched_articles_skip_fetch(self, mock_topics, mock_chat, config):
        mock_chat.return_value = [
            {"topic": "t", "title": "t", "description": "d", "categories": ["Privacy"]},
        ]
        pre_fetched = [
            {"title": "Pre", "source": "s", "link": "", "description": "", "published": ""},
        ]
        with patch("engine.scanner.fetch_articles") as mock_fetch:
            detect_signals(config, articles=pre_fetched)
            mock_fetch.assert_not_called()

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.fetch_articles")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_empty_categories_returns_empty(self, mock_topics, mock_fetch, mock_chat):
        empty_config = DomainConfig(
            name="Test", persona="A", description="T",
            categories=[], feeds=["https://f.com/rss"],
            detection_prompt="",
        )
        mock_fetch.return_value = []
        result = detect_signals(empty_config)
        assert result == []
        mock_chat.assert_not_called()

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.fetch_articles")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_all_batches_fail(self, mock_topics, mock_fetch, mock_chat, config):
        mock_fetch.return_value = [
            {"title": "T", "source": "s", "link": "", "description": "", "published": ""},
        ]
        mock_chat.side_effect = RuntimeError("LLM down")
        result = detect_signals(config)
        assert result == []
