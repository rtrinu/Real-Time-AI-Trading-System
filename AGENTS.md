# AGENTS.md

## Project overview

Real-time AI trading system. FastAPI backend, PostgreSQL (SQLModel + Alembic), Redis streams, ML pipelines (PyTorch, XGBoost, FinBERT). Early-stage — `src/api/` is mostly empty, the live app entrypoint is root `main.py`.

## Commands

```bash
# Package manager
uv sync

# Run dev server (from repo root — root main.py is the working entrypoint)
uv run uvicorn main:app --reload

# Run tests
uv run pytest

# Alembic migrations (DB_URL comes from .env)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

No linter, formatter, or typecheck is configured. No CI exists yet.

## Import path gotcha

`src/` is the package root but is **not** a package itself. Modules like `core`, `db`, `pipeline`, `ingestion` live inside `src/` and are imported bare (`from core.config import settings`). If you add new entrypoints or scripts, ensure `src/` is on `PYTHONPATH` or the working directory so these bare imports resolve.

The README references `src.api.main:app` but `src/api/main.py` does not exist. The actual app is root `main.py`. Tests import `from api.main` which also doesn't resolve currently.

## Infrastructure prerequisites

- **PostgreSQL** — `DB_URL` in `.env` (psycopg dialect)
- **Redis** — `REDIS_URL` in `.env`, used by `src/streaming/`
- `.env` is gitignored. Required keys: `REDIS_URL`, `FINNHUB_API`, `DB_URL`, `NEWSAPI_KEY`

## Architecture

```
main.py                  ← FastAPI app + startup hooks (news pipeline runs on boot)
src/
  core/config.py         ← Pydantic Settings, loads .env
  db/                    ← SQLModel models (market_models, news_models), engine, CRUD
  db/crud/general.py     ← Generic bulk_insert(df, model, session) used by all pipelines
  ingestion/             ← Data fetchers (yfinance, NewsAPI)
  pipeline/              ← Orchestrators: run_newsapi_pipeline, run_yfinance_pipeline
  features/              ← Feature engineering (market indicators, FinBERT sentiment)
  ml/                    ← XGBoost wrapper (early)
  streaming/             ← Redis Streams market tick publisher
```

## Testing

- pytest with `asyncio_mode = auto` (`pytest.ini`)
- Only 2 test files exist; `test_health.py` works, `test_data_source.py` is empty
- Tests require the app to import cleanly, which means DB + .env must be present or imports must be mocked

## Conventions

- SQLModel for all DB models; table classes use `table=True` and explicit `__tablename__`
- Pydantic `BaseSettings` for config (reads `.env` at module import time via `core.config`)
- `db.create_engine.get_session()` returns a raw SQLModel `Session` (not async) — used directly in pipelines
- Pipelines are synchronous functions called from async startup hooks
- Alembic `env.py` imports all models from `db.market_models` and `db.news_models` for autogenerate
