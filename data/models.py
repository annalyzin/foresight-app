from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class SourceArticle(BaseModel):
    title: str
    url: str = ""
    source: str = ""
    description: str = ""


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    domain: str
    topic: str = ""  # Granular label, e.g. "Youth social media bans"
    categories: List[str] = Field(default_factory=list)  # Broad themes
    title: str
    description: str
    strength_score: int = Field(ge=1, le=10)
    reasoning: str
    sources: List[str] = Field(default_factory=list)
    source_url: str = ""
    source_quote: str = ""
    source_articles: List[SourceArticle] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
