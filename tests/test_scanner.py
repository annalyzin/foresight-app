from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config.base import DomainConfig
from data.models import Signal
from engine.scanner import _build_windows, _parse_signals, backfill_signals, detect_signals


from datetime import datetime


SAMPLE_ARTICLES = [
    {"title": "Test", "source": "src", "link": "", "description": "", "published": ""},
]


@pytest.fixture
def config():
    return DomainConfig(
        name="Test Domain",
        persona="Analyst",
        description="Test",
        categories=["Antitrust", "Privacy", "AI Governance"],
        detection_prompt="Categories: {categories}\nTopics: {existing_topics}\nArticles:\n{articles}",
        keywords=["tech antitrust", "data privacy"],
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
            categories=[], detection_prompt="",
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

    def test_parse_skips_non_dict_items(self, config):
        data = [
            {"topic": "valid", "title": "t", "description": "d",
             "categories": ["Privacy"]},
            "string item",
            None,
            42,
        ]
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].topic == "valid"

    def test_parse_skips_non_dict_related_articles(self, config):
        data = [
            {"topic": "t", "title": "t", "description": "d",
             "categories": ["Privacy"],
             "related_articles": [
                 {"title": "Good", "url": "https://example.com", "source": "Reuters"},
                 "bad",
                 None,
             ]},
        ]
        signals = _parse_signals(data, config)
        assert len(signals[0].source_articles) == 1
        assert signals[0].source_articles[0].title == "Good"

    def test_empty_categories_list_fallback(self, config):
        data = [{"topic": "t", "title": "t", "description": "d", "categories": []}]
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].categories == ["Antitrust"]

    def test_parse_dict_without_signals_key(self, config):
        data = {"topic": "X", "title": "Y", "description": "d",
                "categories": ["Privacy"]}
        signals = _parse_signals(data, config)
        assert len(signals) == 1
        assert signals[0].topic == "X"
        assert signals[0].title == "Y"


class TestDetectSignals:
    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_pipeline(self, mock_topics, mock_chat, config):
        mock_chat.return_value = [
            {"topic": "AI rules", "title": "New AI rules", "description": "d",
             "categories": ["AI Governance"], "sources": ["Reuters"]},
        ]
        signals = detect_signals(config, articles=SAMPLE_ARTICLES)
        assert len(signals) >= 1
        assert all(isinstance(s, Signal) for s in signals)

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_batch_failure_continues(self, mock_topics, mock_chat, config):
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

        signals = detect_signals(config, articles=SAMPLE_ARTICLES)
        # First batch fails, but other batches succeed
        assert len(signals) >= 1

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_callbacks_invoked(self, mock_topics, mock_chat, config):
        mock_chat.return_value = [
            {"topic": "t", "title": "t", "description": "d", "categories": ["Privacy"]},
        ]
        on_start = MagicMock()
        on_end = MagicMock()
        detect_signals(config, articles=SAMPLE_ARTICLES, on_category_start=on_start, on_category_end=on_end)
        assert on_start.call_count == len(config.categories)
        assert on_end.call_count == len(config.categories)
        # First call should be (0, total_batches, [first_category])
        first_start_args = on_start.call_args_list[0][0]
        assert first_start_args[0] == 0
        assert first_start_args[1] == len(config.categories)

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_pre_fetched_articles(self, mock_topics, mock_chat, config):
        mock_chat.return_value = [
            {"topic": "t", "title": "t", "description": "d", "categories": ["Privacy"]},
        ]
        pre_fetched = [
            {"title": "Pre", "source": "s", "link": "", "description": "", "published": ""},
        ]
        signals = detect_signals(config, articles=pre_fetched)
        assert len(signals) >= 1

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_empty_categories_returns_empty(self, mock_topics, mock_chat):
        empty_config = DomainConfig(
            name="Test", persona="A", description="T",
            categories=[], detection_prompt="",
        )
        result = detect_signals(empty_config, articles=[])
        assert result == []
        mock_chat.assert_not_called()

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_empty_articles_returns_early(self, mock_topics, mock_chat, config):
        result = detect_signals(config, articles=[])
        assert result == []
        mock_chat.assert_not_called()

    @patch("engine.scanner.chat_json")
    @patch("engine.scanner.get_existing_topics", return_value=set())
    def test_all_batches_fail(self, mock_topics, mock_chat, config):
        mock_chat.side_effect = RuntimeError("LLM down")
        result = detect_signals(config, articles=SAMPLE_ARTICLES)
        assert result == []


class TestBuildWindows:
    def test_exact_three_month_windows(self):
        start = datetime(2023, 1, 1)
        end = datetime(2024, 1, 1)
        windows = _build_windows(start, end, months=3)
        # ~365 days / 90 days per window ≈ 4-5 windows
        assert len(windows) >= 4
        assert windows[0][0] == start
        assert windows[-1][1] == end

    def test_short_range_single_window(self):
        start = datetime(2025, 1, 1)
        end = datetime(2025, 2, 1)
        windows = _build_windows(start, end, months=3)
        assert len(windows) == 1
        assert windows[0] == (start, end)

    def test_windows_are_contiguous(self):
        start = datetime(2022, 6, 1)
        end = datetime(2023, 6, 1)
        windows = _build_windows(start, end, months=3)
        for i in range(len(windows) - 1):
            assert windows[i][1] == windows[i + 1][0]

    def test_last_window_ends_at_end_date(self):
        start = datetime(2023, 1, 1)
        end = datetime(2023, 7, 15)
        windows = _build_windows(start, end, months=3)
        assert windows[-1][1] == end


class TestBackfillSignals:
    @patch("engine.scanner.append_signals")
    @patch("engine.scanner.detect_signals")
    @patch("engine.scanner.fetch_gdelt_articles")
    def test_calls_pipeline_per_window(self, mock_gdelt, mock_detect, mock_append, config):
        mock_gdelt.return_value = [
            {"title": "T", "source": "s", "link": "", "description": "", "published": ""},
        ]
        mock_detect.return_value = [
            Signal(domain="Test Domain", topic="t", categories=["Antitrust"],
                   title="t", description="d", strength_score=5,
                   reasoning="r", sources=["s"]),
        ]

        start = datetime(2025, 1, 1)
        end = datetime(2025, 4, 1)  # ~1 window of 3 months
        total = backfill_signals(config, start, end)

        assert total >= 1
        assert mock_gdelt.call_count >= 1
        assert mock_detect.call_count >= 1
        assert mock_append.call_count >= 1

    @patch("engine.scanner.append_signals")
    @patch("engine.scanner.detect_signals")
    @patch("engine.scanner.fetch_gdelt_articles")
    def test_skips_empty_windows(self, mock_gdelt, mock_detect, mock_append, config):
        mock_gdelt.return_value = []

        start = datetime(2025, 1, 1)
        end = datetime(2025, 4, 1)
        total = backfill_signals(config, start, end)

        assert total == 0
        mock_detect.assert_not_called()
        mock_append.assert_not_called()

    @patch("engine.scanner.append_signals")
    @patch("engine.scanner.detect_signals")
    @patch("engine.scanner.fetch_gdelt_articles")
    def test_progress_callback(self, mock_gdelt, mock_detect, mock_append, config):
        mock_gdelt.return_value = []
        on_progress = MagicMock()

        start = datetime(2023, 1, 1)
        end = datetime(2024, 1, 1)
        backfill_signals(config, start, end, on_progress=on_progress)

        assert on_progress.call_count >= 4
        first_call = on_progress.call_args_list[0][0]
        assert first_call[0] == 0  # window_index
        assert first_call[1] >= 4  # total_windows

    @patch("engine.scanner.append_signals")
    @patch("engine.scanner.score_signals")
    @patch("engine.scanner.detect_signals")
    @patch("engine.scanner.fetch_gdelt_articles")
    def test_backfilled_signals_are_scored(self, mock_gdelt, mock_detect, mock_score, mock_append, config):
        raw_signals = [
            Signal(domain="Test Domain", topic="t", categories=["Antitrust"],
                   title="t", description="d", strength_score=5,
                   reasoning="r", sources=["s"]),
        ]
        scored_signals = [
            Signal(domain="Test Domain", topic="t", categories=["Antitrust"],
                   title="t", description="d", strength_score=8,
                   reasoning="r", sources=["s"]),
        ]
        mock_gdelt.return_value = [
            {"title": "T", "source": "s", "link": "", "description": "", "published": ""},
        ]
        mock_detect.return_value = raw_signals
        mock_score.return_value = scored_signals

        start = datetime(2025, 1, 1)
        end = datetime(2025, 4, 1)
        backfill_signals(config, start, end)

        mock_score.assert_called()
        # Verify scored signals (not raw) were passed to append
        mock_append.assert_called()
        appended = mock_append.call_args[0][1]
        assert appended[0].strength_score == 8

    @patch("engine.scanner.append_signals")
    @patch("engine.scanner.score_signals", side_effect=lambda s: s)
    @patch("engine.scanner.detect_signals")
    @patch("engine.scanner.fetch_gdelt_articles")
    def test_timestamps_set_to_window_midpoint(self, mock_gdelt, mock_detect, mock_score, mock_append, config):
        mock_gdelt.return_value = [
            {"title": "T", "source": "s", "link": "", "description": "", "published": ""},
        ]
        mock_detect.return_value = [
            Signal(domain="Test Domain", topic="t", categories=["Antitrust"],
                   title="t", description="d", strength_score=5,
                   reasoning="r", sources=["s"]),
        ]

        start = datetime(2025, 1, 1)
        end = datetime(2025, 4, 1)
        backfill_signals(config, start, end)

        mock_append.assert_called()
        appended = mock_append.call_args[0][1]
        expected_midpoint = start + (end - start) / 2
        assert appended[0].timestamp == expected_midpoint


    def test_backfill_rejects_inverted_dates(self, config):
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            backfill_signals(config, datetime(2025, 6, 1), datetime(2025, 1, 1))


class TestDomainConfig:
    def test_keywords_must_be_list(self):
        with pytest.raises(TypeError, match="keywords must be a list"):
            DomainConfig(
                name="Test", persona="A", description="T",
                categories=[], detection_prompt="",
                keywords="not a list",
            )

    def test_keywords_default_to_empty_list(self):
        cfg = DomainConfig(
            name="Test", persona="A", description="T",
            categories=[], detection_prompt="",
        )
        assert cfg.keywords == []
