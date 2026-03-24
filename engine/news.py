from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List

import requests

MAX_ARTICLES_FOR_LLM = 80


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
