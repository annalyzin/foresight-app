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
        detection_prompt="Categories: {categories}\nTopics: {existing_topics}\nArticles:\n{articles}",
    )


@pytest.fixture
def make_signal():
    """Factory fixture for creating test Signal objects."""
    def _make(topic="test topic", title="Test Signal", articles=None, **kwargs):
        source_articles = []
        if articles:
            for t, src in articles:
                source_articles.append(SourceArticle(title=t, url="", source=src))
        defaults = dict(
            domain="Test",
            topic=topic,
            categories=["Cat"],
            title=title,
            description="desc",
            strength_score=5,
            reasoning="",
            source_articles=source_articles,
        )
        defaults.update(kwargs)
        return Signal(**defaults)
    return _make


@pytest.fixture
def signals_dir(tmp_path, monkeypatch):
    """Redirect SIGNALS_DIR to a temp directory."""
    import data.store as store_mod
    monkeypatch.setattr(store_mod, "SIGNALS_DIR", tmp_path)
    return tmp_path
