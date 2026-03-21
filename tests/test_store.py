from __future__ import annotations

import json
from datetime import datetime

import pytest

from data.models import SourceArticle
from data.store import (
    _merge_topic,
    _normalize_topic,
    _signals_path,
    append_signals,
    get_existing_topics,
    load_signals,
    save_signals,
)


class TestStore:
    def test_load_empty(self, signals_dir):
        result = load_signals("Test")
        assert result == []

    def test_save_and_load_roundtrip(self, signals_dir, make_signal):
        original = make_signal(
            source_articles=[
                SourceArticle(title="A1", url="https://example.com", source="Reuters"),
            ],
        )
        save_signals("Test", [original])
        loaded = load_signals("Test")

        assert len(loaded) == 1
        assert loaded[0].topic == "test topic"
        assert loaded[0].title == "Test Signal"
        assert len(loaded[0].source_articles) == 1
        assert loaded[0].source_articles[0].source == "Reuters"

    def test_append_signals(self, signals_dir, make_signal):
        s1 = make_signal(topic="topic1")
        s2 = make_signal(topic="topic2")
        save_signals("Test", [s1])
        append_signals("Test", [s2])

        loaded = load_signals("Test")
        assert len(loaded) == 2
        topics = {s.topic for s in loaded}
        assert topics == {"topic1", "topic2"}

    def test_append_signals_dedup(self, signals_dir, make_signal):
        s1 = make_signal(topic="topic1", title="Title A")
        save_signals("Test", [s1])
        s2 = make_signal(topic="topic1", title="Title A")  # duplicate
        s3 = make_signal(topic="topic2", title="Title B")  # new
        append_signals("Test", [s2, s3])
        loaded = load_signals("Test")
        assert len(loaded) == 2  # s1 + s3, s2 rejected

    def test_get_existing_topics(self, signals_dir, make_signal):
        s1 = make_signal(topic="AI regulation")
        s2 = make_signal(topic="Privacy laws")
        s3 = make_signal(topic="AI regulation")  # duplicate
        save_signals("Test", [s1, s2, s3])

        topics = get_existing_topics("Test")
        assert topics == {"AI regulation", "Privacy laws"}

    def test_datetime_serialization(self, signals_dir, make_signal):
        ts = datetime(2026, 3, 15, 10, 30, 0)
        s = make_signal(timestamp=ts)
        save_signals("Test", [s])
        loaded = load_signals("Test")

        assert loaded[0].timestamp.year == 2026
        assert loaded[0].timestamp.month == 3
        assert loaded[0].timestamp.day == 15

    def test_load_corrupted_json(self, signals_dir):
        path = signals_dir / "test_signals.json"
        path.write_text("{not valid json!!!")
        result = load_signals("Test")
        assert result == []

    def test_load_invalid_signal_data(self, signals_dir):
        path = signals_dir / "test_signals.json"
        # Valid JSON but missing required Signal fields
        path.write_text(json.dumps([{"bad_field": "value"}]))
        result = load_signals("Test")
        assert result == []

    def test_get_existing_topics_filters_empty(self, signals_dir, make_signal):
        s1 = make_signal(topic="Real topic")
        s2 = make_signal(topic="", title="No topic signal")
        save_signals("Test", [s1, s2])
        topics = get_existing_topics("Test")
        assert topics == {"Real topic"}

    def test_signals_path_slugification(self):
        path = _signals_path("Big Tech & AI Policy!")
        assert path.name == "big_tech___ai_policy__signals.json"


class TestNormalizeTopic:
    def test_lowercase_and_strip(self):
        assert _normalize_topic("  AI Governance  ") == "ai governance"

    def test_collapse_whitespace(self):
        assert _normalize_topic("AI   governance  regulation") == "ai governance regulation"

    def test_already_normal(self):
        assert _normalize_topic("antitrust enforcement") == "antitrust enforcement"


class TestMergeTopic:
    def test_exact_match(self):
        existing = {"State antitrust enforcement"}
        assert _merge_topic("State antitrust enforcement", existing) == "State antitrust enforcement"

    def test_fuzzy_match_returns_existing(self):
        existing = {"State antitrust enforcement"}
        result = _merge_topic("State-level antitrust enforcement", existing)
        assert result == "State antitrust enforcement"

    def test_no_match_returns_new(self):
        existing = {"AI governance"}
        result = _merge_topic("Privacy regulation", existing)
        assert result == "Privacy regulation"

    def test_empty_existing(self):
        assert _merge_topic("New topic", set()) == "New topic"

    def test_case_insensitive_fuzzy(self):
        existing = {"AI Governance Regulation"}
        result = _merge_topic("ai governance regulation", existing)
        assert result == "AI Governance Regulation"


class TestAppendSignalsFuzzyDedup:
    def test_fuzzy_topic_merged_on_append(self, signals_dir, make_signal):
        s1 = make_signal(topic="State antitrust enforcement", title="Signal A")
        save_signals("Test", [s1])

        s2 = make_signal(topic="State-level antitrust enforcement", title="Signal B")
        append_signals("Test", [s2])

        loaded = load_signals("Test")
        assert len(loaded) == 2
        # Both should share the original topic label
        topics = {s.topic for s in loaded}
        assert topics == {"State antitrust enforcement"}
