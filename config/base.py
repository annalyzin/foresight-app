from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DomainConfig:
    name: str
    persona: str
    description: str
    categories: List[str]  # Broad themes (internal context)
    key_actors: List[str]
    feeds: List[str]
    detection_prompt: str
