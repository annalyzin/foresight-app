from __future__ import annotations

from typing import List

from data.models import Signal


def score_signal(signal: Signal) -> Signal:
    """Score a signal based on article count. No LLM calls."""
    article_count = len(signal.source_articles)

    if article_count == 0:
        reasoning = "No related articles available for scoring."
    else:
        reasoning = f"Based on {article_count} related article{'s' if article_count != 1 else ''}."

    return signal.model_copy(update={"strength_score": article_count, "reasoning": reasoning})


def score_signals(signals: List[Signal]) -> List[Signal]:
    """Score all signals using the article-count formula."""
    return [score_signal(s) for s in signals]
