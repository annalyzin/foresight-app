from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from data.models import Signal, SourceArticle


def _make_signal(**overrides):
    defaults = dict(
        domain="Test",
        topic="test",
        categories=["Cat"],
        title="Title",
        description="desc",
        strength_score=5,
        reasoning="r",
    )
    defaults.update(overrides)
    return Signal(**defaults)


class TestSignalValidation:
    def test_signal_score_min_boundary(self):
        s = _make_signal(strength_score=1)
        assert s.strength_score == 1

    def test_signal_score_max_boundary(self):
        s = _make_signal(strength_score=10)
        assert s.strength_score == 10

    def test_signal_score_below_min_rejected(self):
        with pytest.raises(ValidationError):
            _make_signal(strength_score=0)

    def test_signal_score_above_max_rejected(self):
        with pytest.raises(ValidationError):
            _make_signal(strength_score=11)

    def test_signal_id_auto_generated(self):
        s1 = _make_signal()
        s2 = _make_signal()
        assert s1.id != s2.id
        assert len(s1.id) == 12

    def test_signal_timestamp_default(self):
        before = datetime.now(timezone.utc)
        s = _make_signal()
        after = datetime.now(timezone.utc)
        assert before <= s.timestamp <= after

    def test_source_article_defaults(self):
        a = SourceArticle(title="Test Article")
        assert a.url == ""
        assert a.source == ""
        assert a.description == ""
