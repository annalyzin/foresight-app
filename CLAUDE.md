# CLAUDE.md

## What is this project?

TrendMill — a weak signal detection dashboard for policy monitoring. It scans historical archives (GDELT), uses an LLM (Gemini 2.5 Flash via OpenRouter) to extract emerging policy signals, scores them, and visualizes trends over time via a Streamlit UI.

## Tech stack

- Python 3, Streamlit, Plotly, Pandas, Pydantic
- OpenRouter API (OpenAI-compatible client) for LLM calls
- requests for GDELT
- pytest for testing

## Project structure

```
app.py              # Streamlit UI (chart, sidebar, signal cards)
config/             # DomainConfig dataclass + per-domain configs (big_tech, sg_manpower)
data/models.py      # Pydantic models: Signal, SourceArticle
data/store.py       # JSON file persistence, topic deduplication
engine/scanner.py   # Signal detection pipeline + historical backfill
engine/llm.py       # LLM client with retry logic + JSON repair strategies
engine/scorer.py    # Scoring: strength = number of related articles
engine/news.py      # GDELT article fetching
signals/            # Runtime JSON storage for detected signals
tests/              # pytest suite
```

## Common commands

```bash
# Run the app
streamlit run app.py

# Run tests
pytest
pytest tests/test_scanner.py -v

# Install dependencies
pip install -r requirements.txt
```

## Environment variables

Set in `.env`:
- `OPENROUTER_API_KEY` (required)
- `OPENROUTER_MODEL` (optional, defaults to `google/gemini-2.5-flash`)
- `OPENROUTER_BASE_URL` (optional, defaults to `https://openrouter.ai/api/v1`)

## Key conventions

- Private functions prefixed with `_`
- Callbacks (`on_batch_start`, `on_batch_end`, `on_retry`, `on_progress`) for progress feedback
- Topic deduplication uses SequenceMatcher + Jaccard similarity
- Atomic file writes (temp file + rename) in store.py
- Signal IDs are 12-char hex (truncated UUID4)
- Tests use fixtures from `conftest.py`, mock external APIs (LLM, GDELT)
- Signal strength = total number of source articles (unbounded integer, 0+)
- Chart aggregates signals by (topic, date), summing article counts
- Topics with ≤3 data points are excluded from the chart
