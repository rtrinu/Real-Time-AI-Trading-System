# Real-Time AI Trading System

An end-to-end automated trading system that ingests market and news data, trains ML models (XGBoost + FinBERT sentiment), generates daily trade signals, and executes them on Alpaca (paper trading) — all behind a secure FastAPI API.

## Highlights

- **Automated trading loop** — scheduled jobs retrain models, predict signals, and place orders on Alpaca paper trading every market day
- **ML pipeline** — ensemble of XGBoost models (momentum, mean-reversion, sentiment) with FinBERT news-sentiment features
- **Walk-forward backtesting** — vectorised backtest engine with rolling re-training, transaction costs, and chart generation
- **Full trade audit trail** — every signal, risk check, validation, and order recorded in Postgres
- **Security & ops** — API-key auth, HTTPS, fail2ban-compatible access logging, Discord notifications, Docker Compose deployment
- **217 passing tests**

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLModel, Alembic |
| Cache/queue | Redis (health-checked only — not yet wired into the pipeline) |
| ML | PyTorch, scikit-learn, XGBoost, FinBERT (transformers) |
| Broker | Alpaca (paper) |
| Data sources | yfinance, Finnhub, NewsAPI |
| Scheduler | APScheduler |
| Deploy | Docker Compose, nginx-less TLS via uvicorn SSL |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          FastAPI app                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ news API │  │ predict  │  │ backtest │  │ trade/      │  │
│  │ /news    │  │ /predict │  │ /backtest│  │ portfolio/  │  │
│  │          │  │          │  │          │  │ orders      │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                             │
│  APScheduler jobs:                                          │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────────────┐     │
│  │ market │ │ news   │ │ retrain  │ │ predict+execute│     │
│  │ data   │ │ ingest │ │ models   │ │ (Alpaca)       │     │
│  └────────┘ └────────┘ └──────────┘ └────────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────────┐
        ▼                   ▼                       ▼
  PostgreSQL          Redis                   Alpaca API
  (features,          (startup health           (paper trading)
   predictions,        check only — not
   audit trail)        yet in use)
```

Data flow: raw OHLCV/news → feature engineering (indicators + FinBERT sentiment) → XGBoost ensembles → signal + confidence → risk checks → Alpaca order → audit record → Discord notification.

## Directory layout

```
main.py                 FastAPI app + startup hooks
src/
  api/routes/           news, predict, backtest, monitoring, trade, portfolio, orders
  backtesting/          vectorised backtest + walk-forward engine, metrics, charts
  broker/               Alpaca client, risk management, trade execution
  core/                 config, auth, health checks, logging, notifications
  db/                   SQLModel models, engine, CRUD
  features/             market indicators + FinBERT sentiment engineering
  ingestion/            yfinance, Finnhub, NewsAPI fetchers
  jobs/                 APScheduler jobs (market, news, model, predict, positions, …)
  ml/                   XGBoost wrapper
  pipeline/             orchestrators (market data, news)
  scripts/              utilities (backfill, grid search)
  training/             data loader, trainer, model configs
models/                 trained model artifacts
backtest_results/       generated backtest charts
tests/                  217 tests
```

## Quick start (local dev)

```bash
# 1. Install dependencies
uv sync

# 2. Copy and fill in .env (see .env.example)
cp .env.example .env

# 3. Start PostgreSQL + Redis
make infra

# 4. Run migrations
uv run alembic upgrade head

# 5. Run the app — on first boot it backfills ~2 years of
#    market data + news sentiment and trains initial models
uv run uvicorn main:app --reload
```

On startup the app waits for Postgres, Redis, and Alpaca, then seeds empty databases automatically, trains the initial model ensemble, and starts all scheduled jobs.

## API endpoints

All endpoints require the `API_KEY` (send as `X-API-Key` header).

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/news/backfill/{symbol}/{start}/{end}` | Backfill news + sentiment |
| POST | `/predict` | Generate a signal for a symbol |
| POST | `/backtest` | Run a vectorised backtest |
| POST | `/trade` | Manually execute a signal on Alpaca |
| GET | `/portfolio` | Current Alpaca portfolio |
| GET | `/orders` | List/cancel orders, close positions |
| GET | `/monitoring/accuracy` | Rolling prediction accuracy |
| GET | `/monitoring/predictions` | Recent predictions |
| GET | `/monitoring/audit` | Trade audit log |

## Deployment

```bash
# Build and run the full stack (app + postgres + redis) behind TLS
docker compose up -d --build
```

Serves the API on `0.0.0.0:8443` with SSL, writes fail2ban-compatible access logs to `./logs`, and runs the trading pipeline automatically.

## Tests

```bash
uv run pytest
```

217 tests covering the backtest engine, broker/risk logic, feature engineering, ML training, API routes, and schedulers.

## Roadmap

- React frontend for monitoring/backtesting dashboards
- Additional signals and model families
- Live (non-paper) trading mode with additional risk controls
