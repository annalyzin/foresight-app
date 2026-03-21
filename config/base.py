from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DomainConfig:
    name: str
    persona: str
    description: str
    categories: List[str]  # Broad themes (internal context)
    feeds: List[str]
    detection_prompt: str
    keywords: List[str] = None  # Search phrases for GDELT historical backfill
    single_theme: bool = False  # TEMP FLAG: limit scan to first category only

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.single_theme:
            self.categories = self.categories[:1]
