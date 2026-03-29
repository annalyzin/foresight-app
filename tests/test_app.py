from __future__ import annotations

import pandas as pd

from app import _build_chart_figure


def _make_agg_df(topics: list[str]) -> pd.DataFrame:
    """Create a minimal aggregated dataframe for chart testing."""
    rows = [{"topic": t, "date": "2026-03-15", "strength_score": 5} for t in topics]
    return pd.DataFrame(rows)


class TestChartXAxis:
    def test_tickformat_is_date(self):
        fig = _build_chart_figure(_make_agg_df(["topic1"]))
        assert fig.layout.xaxis.tickformat == "%Y-%m-%d"

class TestChartColors:
    def test_colors_unique_for_many_topics(self):
        topics = [f"topic_{i}" for i in range(50)]
        fig = _build_chart_figure(_make_agg_df(topics))
        colors = [trace.marker.color for trace in fig.data]
        assert len(colors) == 50
        assert len(set(colors)) == 50

    def test_single_topic_gets_color(self):
        fig = _build_chart_figure(_make_agg_df(["only topic"]))
        assert fig.data[0].marker.color is not None
        assert fig.data[0].line.color is not None
