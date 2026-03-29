from __future__ import annotations

import pytest

from engine.scorer import score_signal, score_signals


class TestScoreSignal:
    def test_zero_articles(self, make_signal):
        s = score_signal(make_signal(articles=[]))
        assert s.strength_score == 0

    def test_one_article_one_source(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters")]))
        assert s.strength_score == 1

    def test_two_articles_two_sources(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC")]))
        assert s.strength_score == 2

    def test_three_articles_three_sources(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN")]))
        assert s.strength_score == 3

    def test_four_articles(self, make_signal):
        s = score_signal(make_signal(articles=[
            ("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN"), ("a4", "Reuters"),
        ]))
        assert s.strength_score == 4

    def test_three_articles_two_sources(self, make_signal):
        s = score_signal(make_signal(articles=[
            ("a1", "Reuters"), ("a2", "Reuters"), ("a3", "BBC"),
        ]))
        assert s.strength_score == 3

    def test_reasoning_zero_articles(self, make_signal):
        s = score_signal(make_signal(articles=[]))
        assert "No related articles" in s.reasoning

    def test_score_signals_batch(self, make_signal):
        signals = [
            make_signal(articles=[("a1", "Reuters")]),
            make_signal(articles=[("a1", "R"), ("a2", "B")]),
            make_signal(articles=[]),
        ]
        scored = score_signals(signals)
        assert len(scored) == 3
        assert all(s.strength_score >= 0 for s in scored)

    def test_articles_with_empty_source_still_counted(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "")]))
        assert s.strength_score == 2

    def test_rescoring_is_idempotent(self, make_signal):
        s = make_signal(articles=[("a1", "Reuters"), ("a2", "BBC")])
        s1 = score_signal(s)
        score1 = s1.strength_score
        reasoning1 = s1.reasoning
        s2 = score_signal(s1)
        assert s2.strength_score == score1
        assert s2.reasoning == reasoning1

    def test_singular_article_reasoning(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters")]))
        assert "1 related article" in s.reasoning

    def test_plural_articles_reasoning(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC")]))
        assert "2 related articles" in s.reasoning

    def test_score_signal_does_not_mutate_original(self, make_signal):
        original = make_signal(articles=[("a1", "Reuters")])
        original_score = original.strength_score
        original_reasoning = original.reasoning
        score_signal(original)
        assert original.strength_score == original_score
        assert original.reasoning == original_reasoning
