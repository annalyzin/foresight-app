import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from config import DOMAINS
from data.store import append_signals, load_signals
from data.seed import seed_if_empty

st.set_page_config(page_title="TrendMill", page_icon="📡", layout="wide")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📡 TrendMill")
    st.caption("Weak Signal Detection Dashboard")

    domain_name = st.selectbox("Domain", list(DOMAINS.keys()))
    config = DOMAINS[domain_name]

    st.markdown(f"**Persona:** {config.persona}")
    st.markdown(f"_{config.description}_")
    st.divider()

    scan_clicked = st.button("🔍 Scan Now", use_container_width=True)

    st.divider()

    # ── Broad Themes (internal context) ──
    st.subheader("Broad Themes")
    for cat in config.categories:
        st.markdown(f"- {cat}")

    st.divider()

    # ── Sources ──
    st.subheader("Feed Sources")
    for feed_url in config.feeds:
        try:
            domain = feed_url.split("/")[2]
            display = domain.replace("www.", "").replace("news.", "")
            if "google.com" in domain:
                if "q=" in feed_url:
                    query = feed_url.split("q=")[1].split("&")[0].replace("+", " ")
                    display = f"Google News: {query}"
                else:
                    display = "Google News"
            elif "reddit.com" in domain:
                parts = feed_url.rstrip("/").split("/")
                sub = parts[parts.index("r") + 1] if "r" in parts else "reddit"
                display = f"Reddit: r/{sub}"
            elif "hnrss.org" in domain:
                if "q=" in feed_url:
                    query = feed_url.split("q=")[1].split("&")[0].replace("+", " ")
                    display = f"HackerNews: {query}"
                else:
                    display = "HackerNews"
            elif "arxiv.org" in domain:
                display = "arXiv: cs.CY"
            st.markdown(f"- {display}")
        except Exception:
            st.markdown(f"- {feed_url}")

# ── Seed data if empty ───────────────────────────────────────────────────────
seed_if_empty(domain_name, config.categories)

# ── Run scan ─────────────────────────────────────────────────────────────────
if scan_clicked:
    with st.status("Scanning for signals...", expanded=True) as status:
        st.write("Fetching news from RSS feeds...")
        from engine.scanner import detect_signals
        from engine.scorer import score_signals

        new_signals = detect_signals(config)
        st.write(f"Detected {len(new_signals)} signals. Scoring...")

        new_signals = score_signals(new_signals)

        append_signals(domain_name, new_signals)

        status.update(label="Scan complete!", state="complete")

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

        for topic in sorted(df["topic"].unique()):
            topic_df = df[df["topic"] == topic].sort_values("timestamp")
            fig.add_trace(go.Scatter(
                x=topic_df["timestamp"],
                y=topic_df["strength_score"],
                mode="lines+markers",
                name=topic,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=topic_df["hover"],
            ))

        fig.update_layout(
            yaxis=dict(title="Strength Score", range=[0, 10.5]),
            xaxis=dict(title="Date"),
            height=500,
            margin=dict(l=40, r=40, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4, x=0),
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
