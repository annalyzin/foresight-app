from __future__ import annotations

import pytest

from engine.scorer import score_signal, score_signals


class TestScoreSignal:
    def test_zero_articles(self, make_signal):
        s = score_signal(make_signal(articles=[]))
        assert s.strength_score == 1  # clamped to min

    def test_one_article_one_source(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters")]))
        # raw = 1*3 + 1 - 3 = 1
        assert s.strength_score == 1

    def test_two_articles_two_sources(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC")]))
        # raw = 2*3 + 2 - 3 = 5
        assert s.strength_score == 5

    def test_three_articles_three_sources(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN")]))
        # raw = 3*3 + 3 - 3 = 9
        assert s.strength_score == 9

    def test_four_articles_three_sources_clamped(self, make_signal):
        s = score_signal(make_signal(articles=[
            ("a1", "Reuters"), ("a2", "BBC"), ("a3", "CNN"), ("a4", "Reuters"),
        ]))
        # raw = 4*3 + 3 - 3 = 12 → clamped to 10
        assert s.strength_score == 10

    def test_duplicate_sources_counted_once(self, make_signal):
        s = score_signal(make_signal(articles=[
            ("a1", "Reuters"), ("a2", "Reuters"), ("a3", "BBC"),
        ]))
        # 3 articles, 2 unique sources → raw = 3*3 + 2 - 3 = 8
        assert s.strength_score == 8

    def test_reasoning_includes_source_names(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "BBC")]))
        assert "Reuters" in s.reasoning
        assert "BBC" in s.reasoning

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
        assert all(1 <= s.strength_score <= 10 for s in scored)

    def test_articles_with_empty_source_ignored(self, make_signal):
        s = score_signal(make_signal(articles=[("a1", "Reuters"), ("a2", "")]))
        # 2 articles, but only 1 non-empty source → raw = 2*3 + 1 - 3 = 4
        assert s.strength_score == 4
        assert "Reuters" in s.reasoning

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
        assert "1 related article " in s.reasoning
        assert "1 distinct source " in s.reasoning
