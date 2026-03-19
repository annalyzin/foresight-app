from __future__ import annotations

import pytest

from data.models import Signal, SourceArticle
from engine.scorer import score_signal, score_signals


def _make_signal(articles: list[tuple[str, str]] | None = None) -> Signal:
    """Helper to create a Signal with specified (title, source) article pairs."""
    source_articles = []
    if articles:
        for title, source in articles:
            source_articles.append(SourceArticle(title=title, url="", source=source))
    return Signal(
        domain="Test",
        topic="test",
        categories=["Cat"],
        title="Test Signal",
        description="desc",
        strength_score=5,
        reasoning="",
        source_articles=source_articles,
    )


class TestScoreSignal:
    def test_zero_articles(self):
        s = score_signal(_make_signal([]))
        assert s.strength_score == 1  # clamped to min

    def test_one_article_one_source(self):
        s = score_signal(_make_signal([("a1", "Reuters")]))
        # raw = 1*3 + 1 - 3 = 1
        assert s.strength_score == 1

    def test_two_articles_two_sources(self):
        s = score_signal(_make_signal([("a1", "Reuters"), ("a2", "BBC")]))
        # raw = 2*3 + 2 - 3 = 5
        assert s.strength_score == 5

    def test_three_articles_three_sources(self):
        s = score_signal(_make_signal([("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN")]))
        # raw = 3*3 + 3 - 3 = 9
        assert s.strength_score == 9

    def test_four_articles_three_sources_clamped(self):
        s = score_signal(_make_signal([
            ("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN"), ("a4", "Reuters"),
        ]))
        # raw = 4*3 + 3 - 3 = 12 → clamped to 10
        assert s.strength_score == 10

    def test_duplicate_sources_counted_once(self):
        s = score_signal(_make_signal([
            ("a1", "Reuters"), ("a2", "Reuters"), ("a3", "BBC"),
        ]))
        # 3 articles, 2 unique sources → raw = 3*3 + 2 - 3 = 8
        assert s.strength_score == 8

    def test_reasoning_includes_source_names(self):
        s = score_signal(_make_signal([("a1", "Reuters"), ("a2", "BBC")]))
        assert "Reuters" in s.reasoning
        assert "BBC" in s.reasoning

    def test_reasoning_zero_articles(self):
        s = score_signal(_make_signal([]))
        assert "No related articles" in s.reasoning

    def test_score_signals_batch(self):
        signals = [
            _make_signal([("a1", "Reuters")]),
            _make_signal([("a1", "R"), ("a2", "B")]),
            _make_signal([]),
        ]
        scored = score_signals(signals)
        assert len(scored) == 3
        assert all(1 <= s.strength_score <= 10 for s in scored)
