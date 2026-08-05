# AGENTS.md

## Project overview

Real-time AI trading system. FastAPI backend, PostgreSQL (SQLModel + Alembic), ML pipelines (PyTorch, XGBoost, FinBERT), Alpaca paper trading, APScheduler jobs, Docker Compose deployment. The live app entrypoint is root `main.py`.

## Commands

```bash
# Package manager
uv sync

# Run dev server (from repo root — root main.py is the working entrypoint)
uv run uvicorn main:app

# Run tests
uv run pytest

# Alembic migrations (DB_URL comes from .env)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

No linter, formatter, or typecheck is configured. No CI exists yet.

## Import path gotcha

`src/` is the package root but is **not** a package itself. Modules like `core`, `db`, `pipeline`, `ingestion` live inside `src/` and are imported bare (`from core.config import settings`). If you add new entrypoints or scripts, ensure `src/` is on `PYTHONPATH` or the working directory so these bare imports resolve.

The actual app is root `main.py`. Tests import the app via `tests/conftest.py`.

## Infrastructure prerequisites

- **PostgreSQL** — `DB_URL` in `.env` (psycopg dialect)
- **Redis** — `REDIS_URL` in `.env`. Note: Redis is **not properly set up yet** — it's only used for a startup health check (`src/core/health.py`); nothing stores or reads from it, so it is not required for features to work
- `.env` is gitignored. Required keys: `REDIS_URL`, `FINNHUB_API`, `DB_URL`, `NEWSAPI_KEY`, `API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`

## Architecture

```
main.py                  ← FastAPI app + startup hooks (backfills market/news data + trains models on boot)
src/
  api/routes/            ← news, predict, backtest, monitoring, trade, portfolio, orders
  core/config.py         ← Pydantic Settings, loads .env
  db/                    ← SQLModel models (market_models, news_models, prediction_models, trades), engine, CRUD
  db/crud/general.py     ← Generic bulk_insert(df, model, session) used by all pipelines
  ingestion/             ← Data fetchers (yfinance, Finnhub, NewsAPI)
  pipeline/              ← Orchestrators: run_news_pipeline, run_yfinance_pipeline
  features/              ← Feature engineering (market indicators, FinBERT sentiment)
  ml/                    ← XGBoost wrapper
  training/              ← Data loader, trainer, model configs
  backtesting/           ← Vectorised backtest + walk-forward engine, metrics, charts
  broker/                ← Alpaca client, risk checks, order execution, trade audit
  jobs/                  ← APScheduler jobs (market, news, model, predict, positions, fill poller, monitoring)
```

## Testing

- pytest with `asyncio_mode = auto` (`pytest.ini`)
- 217 tests across backtest engine/metrics, broker/risk, feature engineering, ML training, API routes, and schedulers
- Tests require the app to import cleanly, which means DB + .env must be present or imports must be mocked

## Conventions

- SQLModel for all DB models; table classes use `table=True` and explicit `__tablename__`
- Pydantic `BaseSettings` for config (reads `.env` at module import time via `core.config`)
- `db.create_engine.get_session()` returns a raw SQLModel `Session` (not async) — used directly in pipelines
- Pipelines are synchronous functions called from async startup hooks
- Alembic `env.py` imports all models from `db.market_models` and `db.news_models` for autogenerate
