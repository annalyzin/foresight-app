from __future__ import annotations

import math
from typing import List

from data.models import Signal


def score_signal(signal: Signal) -> Signal:
    """Score a signal based on article count and source diversity. No LLM calls."""
    article_count = len(signal.source_articles)
    source_names = sorted({a.source for a in signal.source_articles if a.source})
    source_diversity = len(source_names)

    raw_score = (article_count * 3) + source_diversity - 3
    signal.strength_score = max(1, min(10, math.floor(raw_score + 0.5)))

    # Build reasoning
    if article_count == 0:
        signal.reasoning = "No related articles available for scoring."
    else:
        sources_str = ", ".join(source_names)
        signal.reasoning = (
            f"Based on {article_count} related article{'s' if article_count != 1 else ''} "
            f"from {source_diversity} distinct source{'s' if source_diversity != 1 else ''} "
            f"({sources_str})."
        )

    return signal


def score_signals(signals: List[Signal]) -> List[Signal]:
    """Score all signals using the article-count formula."""
    return [score_signal(s) for s in signals]
