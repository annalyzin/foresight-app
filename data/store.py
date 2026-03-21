from __future__ import annotations

import difflib
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from data.models import Signal

SIGNALS_DIR = Path(__file__).resolve().parent.parent / "signals"


def _ensure_dir():
    SIGNALS_DIR.mkdir(exist_ok=True)


def _signals_path(domain: str) -> Path:
    slug = re.sub(r"[^a-z0-9_]", "_", domain.lower())
    return SIGNALS_DIR / f"{slug}_signals.json"


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


def _normalize_topic(topic: str) -> str:
    """Lowercase, strip, and collapse whitespace."""
    return re.sub(r"\s+", " ", topic.strip().lower())


def _merge_topic(new_topic: str, existing_topics: Set[str], threshold: float = 0.85) -> str:
    """Return the existing topic if fuzzy-similar, otherwise return new_topic as-is."""
    norm_new = _normalize_topic(new_topic)
    for existing in existing_topics:
        norm_existing = _normalize_topic(existing)
        ratio = difflib.SequenceMatcher(None, norm_new, norm_existing).ratio()
        if ratio >= threshold:
            return existing
    return new_topic


def load_signals(domain: str) -> List[Signal]:
    _ensure_dir()
    path = _signals_path(domain)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logging.warning("Corrupted signals file %s — returning empty list", path)
        return []
    try:
        return [Signal(**item) for item in data]
    except Exception as e:
        logging.warning("Invalid signal data in %s: %s — returning empty list", path, e)
        return []


def save_signals(domain: str, signals: List[Signal]):
    _ensure_dir()
    path = _signals_path(domain)
    data = [s.model_dump() for s in signals]
    fd, tmp = tempfile.mkstemp(dir=SIGNALS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, default=_serialize)
        os.replace(tmp, str(path))
    except BaseException:
        # os.fdopen may not have been reached — close fd if still open
        try:
            os.close(fd)
        except OSError:
            pass  # already closed by os.fdopen/with
        raise
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append_signals(domain: str, new_signals: List[Signal]):
    existing = load_signals(domain)
    existing_topics = {s.topic for s in existing if s.topic}

    # Remap near-duplicate topics to existing labels
    for s in new_signals:
        if s.topic:
            merged = _merge_topic(s.topic, existing_topics)
            s.topic = merged
            existing_topics.add(merged)

    seen = {(s.topic, s.title) for s in existing}
    unique_new = [s for s in new_signals if (s.topic, s.title) not in seen]
    existing.extend(unique_new)
    save_signals(domain, existing)


def get_existing_topics(domain: str) -> Set[str]:
    """Return the set of topic labels already used in stored signals."""
    signals = load_signals(domain)
    return {s.topic for s in signals if s.topic}
