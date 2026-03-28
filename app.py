import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

from config import DOMAINS
from data.store import load_signals

st.set_page_config(page_title="TrendMill", page_icon="🏃‍♀️💨", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏃‍♀️💨 TrendMill")
    st.caption("Weak Signal Detection Dashboard")

    domain_name = st.selectbox("Domain", list(DOMAINS.keys()))
    config = DOMAINS[domain_name]

    st.markdown(f"**Persona:** {config.persona}")
    st.markdown(f"_{config.description}_")
    st.divider()

    # ── Historical Backfill ──
    if config.keywords:
        st.subheader("Historical Backfill")
        st.caption("Fetch historical articles from GDELT")
        today = datetime.today().date()
        three_years_ago = today - timedelta(days=3 * 365)
        backfill_cols = st.columns(2)
        with backfill_cols[0]:
            backfill_start = st.date_input("From", value=three_years_ago, key="bf_start")
        with backfill_cols[1]:
            backfill_end = st.date_input("To", value=today, key="bf_end")
        backfill_clicked = st.button("📚 Backfill", use_container_width=True)
    else:
        backfill_clicked = False

    st.divider()

    # ── Broad Themes (internal context) ──
    st.subheader("Broad Themes")
    for cat in config.categories:
        st.markdown(f"- {cat}")

# ── Run backfill ──────────────────────────────────────────────────────────────
if backfill_clicked:
    if not os.getenv("OPENROUTER_API_KEY"):
        st.error("OPENROUTER_API_KEY not set. Add it to your .env file.")
        st.stop()

    with st.status("Running historical backfill...", expanded=True) as status:
        from engine.scanner import backfill_signals

        bf_start_dt = datetime.combine(backfill_start, datetime.min.time())
        bf_end_dt = datetime.combine(backfill_end, datetime.min.time())

        progress_bar = st.progress(0)

        def _on_backfill_progress(window_index, total_windows, label):
            pct = window_index / total_windows
            progress_bar.progress(
                pct,
                text=f"Window {window_index + 1}/{total_windows}: {label}",
            )
            st.write(f"Fetching & scanning window {window_index + 1}/{total_windows}: {label}...")

        total_new = backfill_signals(
            config,
            start_date=bf_start_dt,
            end_date=bf_end_dt,
            on_progress=_on_backfill_progress,
        )
        progress_bar.progress(1.0, text="Done")

        if total_new:
            st.write(f"Backfill complete — {total_new} new signals added.")
            status.update(label="Backfill complete!", state="complete")
        else:
            st.warning("No new signals found in the selected date range.")
            status.update(label="Backfill complete (no new signals)", state="complete")

# ── Load data ────────────────────────────────────────────────────────────────
signals = load_signals(domain_name)

# ── Signal Strength Chart ────────────────────────────────────────────────────
st.header("Signal Strength Over Time")
st.caption(
    "Each point shows the total number of articles for a topic on a given date. "
    "Topics with 3 or fewer data points are hidden."
)

if signals:
    # Build dataframe — one row per signal
    rows = []
    for s in signals:
        if s.topic:
            d = s.model_dump()
            rows.append(d)
    df = pd.DataFrame(rows)

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date

        # Aggregate by (topic, date), summing article counts
        agg = df.groupby(["topic", "date"], as_index=False).agg({"strength_score": "sum"})

        # Filter topics with >3 data points
        topic_counts = agg.groupby("topic")["date"].count()
        valid_topics = topic_counts[topic_counts > 3].index
        agg = agg[agg["topic"].isin(valid_topics)]

        # Topic filter — only offer topics that survived the >3 filter
        all_topics = sorted(agg["topic"].unique())

        selected_topics = st.multiselect(
            "Filter by topic",
            all_topics,
            default=all_topics,
            key="topic_filter",
        )

        agg = agg[agg["topic"].isin(selected_topics)]

        if not agg.empty:
            fig = go.Figure()

            # Build a palette with 50 distinct colors
            _palette = list(px.colors.qualitative.Alphabet) + list(px.colors.qualitative.Dark24)
            sorted_topics = sorted(agg["topic"].unique())
            topic_color = {t: _palette[i % len(_palette)] for i, t in enumerate(sorted_topics)}

            for topic in sorted_topics:
                topic_df = agg[agg["topic"] == topic].sort_values("date")
                fig.add_trace(go.Scatter(
                    x=topic_df["date"],
                    y=topic_df["strength_score"],
                    mode="lines+markers",
                    name=topic,
                    marker=dict(color=topic_color[topic]),
                    line=dict(color=topic_color[topic]),
                    hovertemplate="<b>%{x}</b><br>%{y} articles<extra>%{fullData.name}</extra>",
                ))

            fig.update_layout(
                yaxis=dict(title="# of articles"),
                xaxis=dict(title="Date", tickformat="%Y-%m-%d"),
                height=500,
                margin=dict(l=40, r=40, t=30, b=40),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No signals match the selected topics.")
    else:
        st.info("No signals with topics found.")
else:
    st.info("No signals yet. Use **Backfill** to start.")

# ── Topic Drill-Down ─────────────────────────────────────────────────────────
st.header("Topic Drill-Down")

if signals:
    topics_with_counts = {}
    for s in signals:
        if s.topic:
            topics_with_counts[s.topic] = topics_with_counts.get(s.topic, 0) + 1

    topic_options = sorted(topics_with_counts.keys())

    selected_topic = st.selectbox(
        "Select a topic to view all signals and sources",
        topic_options,
        format_func=lambda t: f"{t} ({topics_with_counts[t]} signals)",
        key="topic_drilldown",
    )

    # Filter signals for this topic
    topic_signals = [s for s in signals if s.topic == selected_topic]
    topic_signals.sort(key=lambda s: s.timestamp, reverse=True)

    if topic_signals:
        # Show broad themes this topic spans
        all_cats = set()
        for s in topic_signals:
            all_cats.update(s.categories)
        st.markdown(f"**{len(topic_signals)} signals** — Themes: _{', '.join(sorted(all_cats))}_")

        for signal in topic_signals:
            if signal.strength_score >= 10:
                badge = "🔴"
            elif signal.strength_score >= 5:
                badge = "🟡"
            else:
                badge = "🟢"

            with st.expander(
                f"{badge} {signal.title} — "
                f"{signal.timestamp.strftime('%Y-%m-%d')}"
            ):
                st.markdown(signal.description)

                if signal.source_quote:
                    st.markdown(f"> _{signal.source_quote}_")

                # Source link
                source_name = ", ".join(signal.sources) if signal.sources else "Unknown"
                if signal.source_url:
                    st.markdown(f"**Primary source:** [{source_name}]({signal.source_url})")

                # All related articles
                if signal.source_articles:
                    st.markdown("**All related coverage:**")
                    for article in signal.source_articles:
                        if article.url:
                            st.markdown(f"- [{article.title}]({article.url}) — _{article.source}_")
                        else:
                            st.markdown(f"- {article.title} — _{article.source}_")


                if len(signal.categories) > 1:
                    st.caption(f"Themes: {', '.join(signal.categories)}")
    else:
        st.info(f"No signals for _{selected_topic}_ yet.")
else:
    st.info("No signals yet.")
