"""Run walk-forward grid search and save best params to models/best_params.json"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json
from itertools import product
from ml.xgboost import XGBoostModel
from backtesting.engine import walk_forward
from core.logger_config import setup_logging, logger

PARAM_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [4, 5, 6],
    "learning_rate": [0.01, 0.05, 0.1],
    "subsample": [0.7, 0.8],
}

FEATURES = ["MomentumFeatures", "Sentiment"]
SIGNAL = "signal_5"
SYMBOL = "AAPL"


def run():
    setup_logging()

    keys = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    combos = list(product(*values))
    logger.info(f"Grid search: {len(combos)} parameter combinations")

    results = []
    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        logger.info(f"[{i+1}/{len(combos)}] Testing: {params}")

        wf_result = walk_forward(
            features=FEATURES,
            signal=SIGNAL,
            symbol=SYMBOL,
            _model_params=params,
        )

        if wf_result:
            m = wf_result["metrics"]
            results.append({"params": params, "metrics": m})
            logger.info(f"  Sharpe: {m['sharpe_ratio']}, Return: {m['total_return']}%, Trades: {m['total_trades']}")

    if not results:
        logger.error("No valid results")
        return

    best = max(results, key=lambda r: r["metrics"]["sharpe_ratio"])
    logger.info(f"\nBest params: {best['params']}")
    logger.info(f"Best metrics: {best['metrics']}")

    os.makedirs("models", exist_ok=True)
    path = os.path.join("models", "best_params.json")
    with open(path, "w") as f:
        json.dump(best, f, indent=2)
    logger.info(f"Saved best params to {path}")


if __name__ == "__main__":
    run()
