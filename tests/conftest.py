from __future__ import annotations

import pytest

from data.models import Signal, SourceArticle


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
            strength_score=0,
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
