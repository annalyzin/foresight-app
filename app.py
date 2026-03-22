import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

from config import DOMAINS
from data.store import append_signals, load_signals
from engine.news import format_feed_source

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

    scan_clicked = st.button("🔍 Scan Now", use_container_width=True)

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

    st.divider()

    # ── Sources ──
    st.subheader("Feed Sources")
    for feed_url in config.feeds:
        st.markdown(f"- {format_feed_source(feed_url)}")

# ── Run scan ─────────────────────────────────────────────────────────────────
if scan_clicked:
    if not os.getenv("OPENROUTER_API_KEY"):
        st.error("OPENROUTER_API_KEY not set. Add it to your .env file.")
        st.stop()

    with st.status("Scanning for signals...", expanded=True) as status:
        st.write("Fetching news from RSS feeds...")
        from engine.scanner import detect_signals
        from engine.scorer import score_signals
        from engine.news import fetch_articles

        articles = fetch_articles(config)
        st.write(f"Fetched {len(articles)} articles from feeds.")

        st.write("Analyzing articles with LLM (this may take a few minutes)...")
        progress_bar = st.progress(0)
        batch_errors = []
        scan_total_batches = [0]

        def _on_batch_start(batch_index, total_batches, batch_categories):
            scan_total_batches[0] = total_batches
            pct = batch_index / total_batches
            progress_bar.progress(
                pct,
                text=f"Batch {batch_index + 1}/{total_batches}: "
                     f"{', '.join(batch_categories)}...",
            )

        def _on_batch_end(batch_index, total_batches, batch_categories, error):
            pct = (batch_index + 1) / total_batches
            progress_bar.progress(pct, text=f"Batch {batch_index + 1}/{total_batches}")
            if error:
                batch_errors.append((batch_categories, error))
                st.warning(
                    f"Batch failed for themes **{', '.join(batch_categories)}**: {error}"
                )
            else:
                st.write(
                    f"Batch {batch_index + 1}/{total_batches} done "
                    f"({', '.join(batch_categories)})"
                )

        def _on_retry(batch_index, total_batches, batch_categories, attempt, max_retries, error_msg):
            st.write(
                f"Batch {batch_index + 1}/{total_batches} "
                f"({', '.join(batch_categories)}) — "
                f"retry {attempt}/{max_retries}: {error_msg}"
            )

        new_signals = detect_signals(
            config,
            articles=articles,
            on_batch_start=_on_batch_start,
            on_batch_end=_on_batch_end,
            on_retry=_on_retry,
        )
        progress_bar.empty()

        if not new_signals and batch_errors:
            st.error(
                f"All {len(batch_errors)} batches failed — no signals detected. "
                "Check your API key and network connection."
            )
            status.update(label="Scan failed", state="error")
        else:
            if batch_errors:
                st.warning(
                    f"{len(batch_errors)} of {scan_total_batches[0]} "
                    f"batch(es) failed. Partial results shown below."
                )
            st.write(f"Detected {len(new_signals)} signals. Scoring...")
            new_signals = score_signals(new_signals)
            append_signals(domain_name, new_signals)
            status.update(label="Scan complete!", state="complete")

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
    "Scores (1\u201310) are derived from article volume and source diversity: "
    "**score = (article count \u00d7 3) + unique sources \u2212 3**, "
    "clamped to 1\u201310. More articles from more sources = stronger signal."
)

if signals:
    # Get all unique topics
    all_topics = sorted({s.topic for s in signals if s.topic})

    # Topic filter
    selected_topics = st.multiselect(
        "Filter by topic",
        all_topics,
        default=all_topics,
        key="topic_filter",
    )

    # Build dataframe — one row per signal, keyed by topic
    rows = []
    for s in signals:
        if s.topic in selected_topics:
            d = s.model_dump()
            rows.append(d)
    df = pd.DataFrame(rows)

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Build hover text
        hover_texts = []
        for _, row in df.iterrows():
            source_name = ", ".join(row["sources"]) if row["sources"] else "Unknown"
            parts = [
                f"<b>{row['title']}</b>",
                f"Topic: {row['topic']}",
                f"Source: {source_name}",
            ]
            if row.get("source_quote"):
                quote = row["source_quote"]
                if len(quote) > 150:
                    quote = quote[:147] + "..."
                parts.append(f"<i>\"{quote}\"</i>")
            n_articles = len(row.get("source_articles", []))
            if n_articles:
                parts.append(f"({n_articles} related articles)")
            hover_texts.append("<br>".join(parts))
        df["hover"] = hover_texts

        fig = go.Figure()

        # Build a palette with 50 distinct colors
        _palette = list(px.colors.qualitative.Alphabet) + list(px.colors.qualitative.Dark24)
        sorted_topics = sorted(df["topic"].unique())
        topic_color = {t: _palette[i % len(_palette)] for i, t in enumerate(sorted_topics)}

        for topic in sorted_topics:
            topic_df = df[df["topic"] == topic].sort_values("timestamp")
            fig.add_trace(go.Scatter(
                x=topic_df["timestamp"],
                y=topic_df["strength_score"],
                mode="lines+markers",
                name=topic,
                marker=dict(color=topic_color[topic]),
                line=dict(color=topic_color[topic]),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=topic_df["hover"],
            ))

        fig.update_layout(
            yaxis=dict(title="Strength Score", range=[0, 10.5]),
            xaxis=dict(title="Date", tickformat="%Y-%m-%d"),
            height=500,
            margin=dict(l=40, r=40, t=30, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signals match the selected topics.")
else:
    st.info("No signals yet. Click **Scan Now** to start.")

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
            if signal.strength_score >= 8:
                badge = "🔴"
            elif signal.strength_score >= 5:
                badge = "🟡"
            else:
                badge = "🟢"

            with st.expander(
                f"{badge} {signal.title} — "
                f"{signal.timestamp.strftime('%Y-%m-%d') if isinstance(signal.timestamp, datetime) else signal.timestamp}"
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
