from __future__ import annotations

import logging
import math
from typing import Callable, List, Optional

from config.base import DomainConfig
from data.models import Signal, SourceArticle
from data.store import get_existing_topics
from engine.llm import chat_json, _sanitize_error
from engine.news import fetch_articles, format_articles_for_llm


def _parse_signals(results, config: DomainConfig) -> List[Signal]:
    """Parse LLM results into Signal objects."""
    if isinstance(results, dict):
        results = results.get("signals", [results])

    signals = []
    for r in results:
        categories = r.get("categories", [])
        if not categories:
            cat = r.get("category", config.categories[0])
            categories = [cat]
        categories = [c for c in categories if c in config.categories]
        if not categories:
            categories = [config.categories[0]]

        source_articles = []
        for ra in r.get("related_articles", []):
            source_articles.append(SourceArticle(
                title=ra.get("title", ""),
                url=ra.get("url", ""),
                source=ra.get("source", ""),
                description=ra.get("description", ""),
            ))

        signals.append(Signal(
            domain=config.name,
            topic=r.get("topic", ""),
            categories=categories,
            title=r.get("title", "Untitled Signal"),
            description=r.get("description", ""),
            strength_score=5,
            reasoning=r.get("reasoning", ""),
            sources=r.get("sources", []),
            source_url=r.get("source_url", ""),
            source_quote=r.get("source_quote", ""),
            source_articles=source_articles,
        ))

    return signals


def detect_signals(
    config: DomainConfig,
    on_batch_start: Optional[Callable[[int, int, List[str]], None]] = None,
    on_batch_end: Optional[Callable[[int, int, List[str], Optional[str]], None]] = None,
    on_retry: Optional[Callable[[int, int, List[str], int, int, str], None]] = None,
) -> List[Signal]:
    """Fetch news and use LLM to detect emerging signals with topic labels.

    Args:
        config: Domain configuration.
        on_batch_start: Called before each batch with
            (batch_index, total_batches, batch_categories).
        on_batch_end: Called after each batch with
            (batch_index, total_batches, batch_categories, error_message_or_None).
        on_retry: Called before each LLM retry with
            (batch_index, total_batches, batch_categories, attempt, max_retries, error_msg).
    """
    articles = fetch_articles(config)
    articles_text = format_articles_for_llm(articles)

    # Load existing topics to inject into prompt for consistency
    existing_topics = get_existing_topics(config.name)
    if existing_topics:
        topics_str = "\n".join(f"- {t}" for t in sorted(existing_topics))
    else:
        topics_str = "(No previous topics — you are starting fresh)"

    all_signals = []

    # Process categories in batches to avoid output truncation
    batch_size = 1
    total_batches = math.ceil(len(config.categories) / batch_size)

    for i in range(0, len(config.categories), batch_size):
        batch_categories = config.categories[i:i + batch_size]
        batch_index = i // batch_size

        if on_batch_start:
            on_batch_start(batch_index, total_batches, batch_categories)

        try:
            batch_prompt = config.detection_prompt.format(
                categories=", ".join(batch_categories),
                existing_topics=topics_str,
                articles=articles_text,
            )
            def _on_llm_retry(attempt, max_retries, error_msg):
                if on_retry:
                    on_retry(batch_index, total_batches, batch_categories, attempt, max_retries, error_msg)

            results = chat_json(batch_prompt, max_tokens=16384, on_retry=_on_llm_retry)
            all_signals.extend(_parse_signals(results, config))
            if on_batch_end:
                on_batch_end(batch_index, total_batches, batch_categories, None)
        except Exception as e:
            error_msg = _sanitize_error(e)
            logging.warning("Batch %s failed: %s", batch_categories, error_msg)
            if on_batch_end:
                on_batch_end(batch_index, total_batches, batch_categories, error_msg)
            continue

    return all_signals
