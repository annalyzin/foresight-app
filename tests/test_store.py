from __future__ import annotations

from datetime import datetime

import pytest

from data.models import Signal, SourceArticle
from data.store import append_signals, get_existing_topics, load_signals, save_signals


def _make_signal(topic: str = "test topic", **kwargs) -> Signal:
    defaults = dict(
        domain="Test",
        topic=topic,
        categories=["Cat"],
        title="Test Signal",
        description="desc",
        strength_score=5,
        reasoning="reason",
    )
    defaults.update(kwargs)
    return Signal(**defaults)


class TestStore:
    def test_load_empty(self, signals_dir):
        result = load_signals("Test")
        assert result == []

    def test_save_and_load_roundtrip(self, signals_dir):
        original = _make_signal(
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

    def test_append_signals(self, signals_dir):
        s1 = _make_signal(topic="topic1")
        s2 = _make_signal(topic="topic2")
        save_signals("Test", [s1])
        append_signals("Test", [s2])

        loaded = load_signals("Test")
        assert len(loaded) == 2
        topics = {s.topic for s in loaded}
        assert topics == {"topic1", "topic2"}

    def test_get_existing_topics(self, signals_dir):
        s1 = _make_signal(topic="AI regulation")
        s2 = _make_signal(topic="Privacy laws")
        s3 = _make_signal(topic="AI regulation")  # duplicate
        save_signals("Test", [s1, s2, s3])

        topics = get_existing_topics("Test")
        assert topics == {"AI regulation", "Privacy laws"}

    def test_datetime_serialization(self, signals_dir):
        ts = datetime(2026, 3, 15, 10, 30, 0)
        s = _make_signal(timestamp=ts)
        save_signals("Test", [s])
        loaded = load_signals("Test")

        assert loaded[0].timestamp.year == 2026
        assert loaded[0].timestamp.month == 3
        assert loaded[0].timestamp.day == 15
