from __future__ import annotations

import pytest

from config.base import DomainConfig
from data.models import Signal, SourceArticle


@pytest.fixture
def sample_signal() -> Signal:
    """A signal with 2 source_articles from 2 different sources."""
    return Signal(
        domain="Big Tech Policy",
        topic="AI governance regulation",
        categories=["AI Governance"],
        title="New AI rules proposed",
        description="Regulators propose new rules for AI systems.",
        strength_score=5,
        reasoning="",
        sources=["Reuters", "TechCrunch"],
        source_url="https://example.com/article",
        source_quote="",
        source_articles=[
            SourceArticle(title="AI rules article", url="https://reuters.com/ai", source="Reuters"),
            SourceArticle(title="AI regulation push", url="https://tc.com/ai", source="TechCrunch"),
        ],
    )


@pytest.fixture
def sample_config() -> DomainConfig:
    """Minimal DomainConfig for testing."""
    return DomainConfig(
        name="Big Tech Policy",
        persona="Google Policy Strategist",
        description="Test domain",
        categories=["Antitrust", "Privacy", "AI Governance"],
        key_actors=["Google", "Meta"],
        feeds=[
            "https://news.google.com/rss/search?q=big+tech",
            "https://feeds.reuters.com/technology",
        ],
        detection_prompt="Categories: {categories}\nTopics: {existing_topics}\nArticles:\n{articles}",
    )


@pytest.fixture
def signals_dir(tmp_path, monkeypatch):
    """Redirect SIGNALS_DIR to a temp directory."""
    import data.store as store_mod
    monkeypatch.setattr(store_mod, "SIGNALS_DIR", tmp_path)
    return tmp_path
