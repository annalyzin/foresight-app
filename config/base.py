from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DomainConfig:
    name: str
    persona: str
    description: str
    categories: List[str]  # Broad themes (internal context)
    detection_prompt: str
    keywords: List[str] = None  # Search phrases for GDELT historical backfill

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
