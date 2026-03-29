from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DomainConfig:
    name: str
    persona: str
    description: str
    categories: List[str]  # Broad themes (internal context)
    detection_prompt: str
    keywords: Optional[List[str]] = None  # Search phrases for GDELT historical backfill

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        elif not isinstance(self.keywords, list):
            raise TypeError(f"keywords must be a list, got {type(self.keywords).__name__}")
