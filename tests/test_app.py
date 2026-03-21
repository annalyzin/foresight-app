from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go


def _build_chart_figure(topics: list[str]) -> go.Figure:
    """Reproduce the color-assignment and layout logic from app.py."""
    _palette = list(px.colors.qualitative.Alphabet) + list(px.colors.qualitative.Dark24)
    sorted_topics = sorted(topics)
    topic_color = {t: _palette[i % len(_palette)] for i, t in enumerate(sorted_topics)}

    fig = go.Figure()
    for topic in sorted_topics:
        fig.add_trace(go.Scatter(
            x=["2026-03-15"],
            y=[5],
            mode="lines+markers",
            name=topic,
            marker=dict(color=topic_color[topic]),
            line=dict(color=topic_color[topic]),
        ))
    fig.update_layout(
        xaxis=dict(title="Date", tickformat="%Y-%m-%d", dtick=86400000),
    )
    return fig


class TestChartXAxis:
    def test_tickformat_is_date(self):
        fig = _build_chart_figure(["topic1"])
        assert fig.layout.xaxis.tickformat == "%Y-%m-%d"

    def test_dtick_is_one_day(self):
        fig = _build_chart_figure(["topic1"])
        assert fig.layout.xaxis.dtick == 86400000


class TestChartColors:
    def test_colors_unique_for_many_topics(self):
        topics = [f"topic_{i}" for i in range(50)]
        fig = _build_chart_figure(topics)
        colors = [trace.marker.color for trace in fig.data]
        assert len(colors) == 50
        assert len(set(colors)) == 50

    def test_single_topic_gets_color(self):
        fig = _build_chart_figure(["only topic"])
        assert fig.data[0].marker.color is not None
        assert fig.data[0].line.color is not None
