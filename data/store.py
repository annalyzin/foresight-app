from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Set

from data.models import Signal

SIGNALS_DIR = Path(__file__).resolve().parent.parent / "signals"


def _ensure_dir():
    SIGNALS_DIR.mkdir(exist_ok=True)


def _signals_path(domain: str) -> Path:
    slug = domain.lower().replace(" ", "_")
    return SIGNALS_DIR / f"{slug}_signals.json"


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


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
    except Exception:
        logging.warning("Invalid signal data in %s — returning empty list", path)
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
        os.unlink(tmp)
        raise


def append_signals(domain: str, new_signals: List[Signal]):
    existing = load_signals(domain)
    existing.extend(new_signals)
    save_signals(domain, existing)


def get_existing_topics(domain: str) -> Set[str]:
    """Return the set of topic labels already used in stored signals."""
    signals = load_signals(domain)
    return {s.topic for s in signals if s.topic}
