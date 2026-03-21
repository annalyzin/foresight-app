from __future__ import annotations

import calendar
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Dict, List

import feedparser

from config.base import DomainConfig


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
            except Exception:
                continue
    return None


def fetch_articles(config: DomainConfig, days: int = 7) -> List[Dict]:
    """Fetch recent articles from all RSS feeds for a domain."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    seen_titles = set()

    for feed_url in config.feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:40]:  # cap per feed
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Simple dedup by normalized title
                title_lower = title.lower()
                if title_lower in seen_titles:
                    continue
                seen_titles.add(title_lower)

                pub_date = _parse_date(entry)
                if pub_date and pub_date < cutoff:
                    continue

                articles.append({
                    "title": title,
                    "description": entry.get("summary", entry.get("description", ""))[:500],
                    "link": entry.get("link", ""),
                    "published": pub_date.isoformat() if pub_date else "",
                    "source": urlparse(feed_url).netloc or feed_url,
                })
        except Exception as e:
            logging.warning("Failed to fetch feed %s: %s", feed_url, e)
            continue

    return articles


def format_articles_for_llm(articles: List[Dict]) -> str:
    """Format articles into a text block for LLM consumption."""
    if not articles:
        return "No recent articles found."

    lines = []
    for i, a in enumerate(articles[:80], 1):  # cap at 80 for context limits
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("link"):
            lines.append(f"   URL: {a['link']}")
        if a.get("description"):
            # Strip HTML tags from description
            desc = re.sub(r"<[^>]+>", "", a["description"])
            lines.append(f"   {desc[:200]}")
        lines.append("")
    return "\n".join(lines)
