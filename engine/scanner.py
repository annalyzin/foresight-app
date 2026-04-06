from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from config.base import DomainConfig
from data.models import Signal, SourceArticle
from data.store import append_signals, get_existing_topics
from openai import APIError

from engine.llm import chat_json, sanitize_error
from engine.news import fetch_gdelt_articles, format_articles_for_llm
from engine.scorer import score_signals


def _parse_signals(results, config: DomainConfig) -> List[Signal]:
    """Parse LLM results into Signal objects."""
    if not config.categories:
        return []

    if isinstance(results, dict):
        results = results.get("signals", [results])

    signals = []
    for r in results:
        if not isinstance(r, dict):
            continue
        categories = r.get("categories", [])
        if not categories:
            cat = r.get("category", config.categories[0])
            categories = [cat]
        categories = [c for c in categories if c in config.categories]
        if not categories:
            categories = [config.categories[0]]

        source_articles = []
        for ra in r.get("related_articles", []):
            if not isinstance(ra, dict):
                continue
            source_articles.append(SourceArticle(
                title=ra.get("title", ""),
                url=ra.get("url", ""),
                source=ra.get("source", ""),
                description=ra.get("description", ""),
            ))

        # Deduplicate articles by URL (or title if no URL)
        seen = set()
        unique_articles = []
        for sa in source_articles:
            key = sa.url if sa.url else sa.title
            if key and key not in seen:
                seen.add(key)
                unique_articles.append(sa)
        source_articles = unique_articles

        signals.append(Signal(
            domain=config.name,
            topic=r.get("topic", ""),
            categories=categories,
            title=r.get("title", "Untitled Signal"),
            description=r.get("description", ""),
            strength_score=0,
            reasoning=r.get("reasoning", ""),
            sources=r.get("sources", []),
            source_url=r.get("source_url", ""),
            source_quote=r.get("source_quote", ""),
            source_articles=source_articles,
        ))

    return signals


def detect_signals(
    config: DomainConfig,
    articles: List[dict],
    on_category_start: Optional[Callable[[int, int, List[str]], None]] = None,
    on_category_end: Optional[Callable[[int, int, List[str], Optional[str]], None]] = None,
    on_retry: Optional[Callable[[int, int, List[str], int, int, str], None]] = None,
) -> List[Signal]:
    """Use LLM to detect emerging signals with topic labels.

    Args:
        config: Domain configuration.
        articles: Pre-fetched articles to analyze.
        on_category_start: Called before each category with
            (category_index, total_categories, category_list).
        on_category_end: Called after each category with
            (category_index, total_categories, category_list, error_message_or_None).
        on_retry: Called before each LLM retry with
            (batch_index, total_batches, category_list, attempt, max_retries, error_msg).
    """
    if not articles:
        return []

    articles_text = format_articles_for_llm(articles)

    # Load existing topics to inject into prompt for consistency
    existing_topics = get_existing_topics(config.name)
    if existing_topics:
        topics_str = "\n".join(f"- {t}" for t in sorted(existing_topics))
    else:
        topics_str = "(No previous topics — you are starting fresh)"

    all_signals = []

    # Process categories one at a time to avoid output truncation
    total_batches = len(config.categories)

    for batch_index, category in enumerate(config.categories):
        # Single-element list to match the prompt's {categories} format
        category_list = [category]

        if on_category_start:
            on_category_start(batch_index, total_batches, category_list)

        try:
            batch_prompt = config.detection_prompt.format(
                categories=", ".join(category_list),
                existing_topics=topics_str,
                articles=articles_text,
            )
            def _on_llm_retry(attempt, max_retries, error_msg):
                if on_retry:
                    on_retry(batch_index, total_batches, category_list, attempt, max_retries, error_msg)

            results = chat_json(batch_prompt, max_tokens=32768, on_retry=_on_llm_retry)
            all_signals.extend(_parse_signals(results, config))
            if on_category_end:
                on_category_end(batch_index, total_batches, category_list, None)
        except (APIError, ValueError, json.JSONDecodeError) as e:
            error_msg = sanitize_error(e)
            logging.warning("Category %s failed: %s", category_list, error_msg)
            if on_category_end:
                on_category_end(batch_index, total_batches, category_list, error_msg)
            continue
        except Exception as e:
            error_msg = sanitize_error(e)
            logging.error(
                "Category %s failed with unexpected error: %s\n%s",
                category_list, error_msg, traceback.format_exc(),
            )
            if on_category_end:
                on_category_end(batch_index, total_batches, category_list, error_msg)
            continue

    return all_signals


def _build_windows(
    start_date: datetime, end_date: datetime, months: int = 3
) -> List[tuple[datetime, datetime]]:
    """Split a date range into windows of approximately `months` months."""
    windows = []
    cursor = start_date
    while cursor < end_date:
        window_end = cursor + timedelta(days=months * 30)
        if window_end > end_date:
            window_end = end_date
        windows.append((cursor, window_end))
        cursor = window_end
    return windows


def backfill_signals(
    config: DomainConfig,
    start_date: datetime,
    end_date: datetime,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> int:
    """Fetch historical articles from GDELT and run through the LLM pipeline.

    Args:
        config: Domain configuration (must have keywords).
        start_date: Start of backfill range.
        end_date: End of backfill range.
        on_progress: Called with (window_index, total_windows, label) for each window.

    Returns:
        Total number of new signals detected.
    """
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")
    windows = _build_windows(start_date, end_date)
    total_windows = len(windows)
    total_signals = 0

    for i, (win_start, win_end) in enumerate(windows):
        label = f"{win_start.strftime('%Y-%m')} to {win_end.strftime('%Y-%m')}"
        if on_progress:
            on_progress(i, total_windows, label)

        articles = fetch_gdelt_articles(config.keywords, win_start, win_end)
        if not articles:
            continue

        signals = detect_signals(config, articles=articles)

        # Resolve per-signal timestamps from actual article publication dates
        pub_dates = {}
        for a in articles:
            if a.get("published"):
                try:
                    pub_dates[a["title"]] = datetime.fromisoformat(a["published"])
                except (ValueError, TypeError):
                    pass

        midpoint = win_start + (win_end - win_start) / 2

        resolved = []
        for s in signals:
            article_dates = [
                pub_dates[sa.title] for sa in s.source_articles if sa.title in pub_dates
            ]
            timestamp = max(article_dates) if article_dates else midpoint
            resolved.append(s.model_copy(update={"timestamp": timestamp}))
        signals = resolved

        if signals:
            signals = score_signals(signals)
            append_signals(config.name, signals)
            total_signals += len(signals)

    return total_signals
