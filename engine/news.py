from __future__ import annotations

import calendar
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Dict, List

import feedparser
import requests

from config.base import DomainConfig

MAX_ENTRIES_PER_FEED = 40
MAX_DESCRIPTION_LENGTH = 500
MAX_ARTICLES_FOR_LLM = 80


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
            except Exception:
                continue
    return None


def format_feed_source(feed_url: str) -> str:
    """Extract human-readable display name from a feed URL."""
    try:
        domain = urlparse(feed_url).netloc.replace("www.", "").replace("news.", "")
        if "google.com" in domain:
            if "q=" in feed_url:
                query = feed_url.split("q=")[1].split("&")[0].replace("+", " ")
                return f"Google News: {query}"
            return "Google News"
        if "reddit.com" in domain:
            parts = feed_url.rstrip("/").split("/")
            r_idx = parts.index("r") if "r" in parts else -1
            sub = parts[r_idx + 1] if r_idx >= 0 and r_idx + 1 < len(parts) else "reddit"
            return f"Reddit: r/{sub}"
        if "hnrss.org" in domain:
            if "q=" in feed_url:
                query = feed_url.split("q=")[1].split("&")[0].replace("+", " ")
                return f"HackerNews: {query}"
            return "HackerNews"
        if "arxiv.org" in domain:
            return "arXiv: cs.CY"
        return domain
    except Exception:
        return feed_url


def fetch_articles(config: DomainConfig, days: int = 7) -> List[Dict]:
    """Fetch recent articles from all RSS feeds for a domain."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    seen_titles = set()

    for feed_url in config.feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Simple dedup by normalized title
                title_lower = title.lower()
                if title_lower in seen_titles:
                    continue
                seen_titles.add(title_lower)

                pub_date = _parse_date(entry)
                if pub_date is None or pub_date < cutoff:
                    continue

                articles.append({
                    "title": title,
                    "description": entry.get("summary", entry.get("description", ""))[:MAX_DESCRIPTION_LENGTH],
                    "link": entry.get("link", ""),
                    "published": pub_date.isoformat() if pub_date else "",
                    "source": urlparse(feed_url).netloc or feed_url,
                })
        except Exception as e:
            logging.warning("Failed to fetch feed %s: %s", feed_url, e)
            continue

    return articles


def fetch_gdelt_articles(
    keywords: List[str],
    start_date: datetime,
    end_date: datetime,
) -> List[Dict]:
    """Fetch historical articles from GDELT for the given keywords and date range."""
    seen_titles: set[str] = set()
    articles: List[Dict] = []

    start_str = start_date.strftime("%Y%m%d%H%M%S")
    end_str = end_date.strftime("%Y%m%d%H%M%S")

    for keyword in keywords:
        try:
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": keyword,
                    "mode": "artlist",
                    "maxrecords": "250",
                    "startdatetime": start_str,
                    "enddatetime": end_str,
                    "format": "json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logging.warning("GDELT query failed for %r: %s", keyword, e)
            continue

        for art in data.get("articles", []):
            title = (art.get("title") or "").strip()
            if not title:
                continue
            title_lower = title.lower()
            if title_lower in seen_titles:
                continue
            seen_titles.add(title_lower)

            # Parse GDELT seendate (YYYYMMDDTHHMMSSZ)
            pub_date = ""
            seen_raw = art.get("seendate", "")
            if seen_raw:
                try:
                    dt = datetime.strptime(seen_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                    pub_date = dt.isoformat()
                except ValueError:
                    pub_date = seen_raw

            articles.append({
                "title": title,
                "description": "",
                "link": art.get("url", ""),
                "published": pub_date,
                "source": art.get("domain", ""),
            })

            if len(articles) >= MAX_ARTICLES_FOR_LLM:
                return articles

    return articles


def format_articles_for_llm(articles: List[Dict]) -> str:
    """Format articles into a text block for LLM consumption."""
    if not articles:
        return "No recent articles found."

    lines = []
    for i, a in enumerate(articles[:MAX_ARTICLES_FOR_LLM], 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("link"):
            lines.append(f"   URL: {a['link']}")
        if a.get("description"):
            # Strip HTML tags from description
            desc = html.unescape(re.sub(r"<[^>]+>", "", a["description"]))
            lines.append(f"   {desc[:200]}")
        lines.append("")
    return "\n".join(lines)
