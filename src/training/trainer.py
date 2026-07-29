from sklearn.model_selection import train_test_split
from ml.xgboost import XGBoostModel
from training.data_loader import load_training_data, load_latest_features
from core.logger_config import logger
import os
import json
from itertools import product
from db.crud.general import bulk_insert
import pandas as pd
from db.prediction_models import Prediction
from db.create_engine import get_session
from datetime import datetime, timezone


def create_split(X, y, test_ratio=0.2):
    split = int(len(X) * (1 - test_ratio))
    x_train, x_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    return x_train, x_test, y_train, y_test


def train(model_type, features, signal, symbol):
    X, y = load_training_data(symbol, features, signal)
    x_train, x_test, y_train, y_test = create_split(X, y)
    model_type.train(x_train, y_train, x_val=x_test, y_val=y_test)
    evaluate = model_type.evaluate(x_test, y_test)
    logger.info(evaluate)


def predict(model_type, features: list[str], signal: str, symbol: str):
    x_latest, date = load_latest_features(features, symbol, signal)

    if x_latest.empty:
        logger.warning(f"No features available for prediction: {symbol}")
        return {"signal": "hold", "confidence": 0.0, "date": ""}

    prediction = model_type.predict(x_latest)[0]
    confidence = model_type.predict_proba(x_latest).max()
    signal_map = {0: "sell", 1: "hold", 2: "buy"}

    return {
        "signal": signal_map[prediction],
        "confidence": float(confidence),
        "date": date,
    }


def ensemble_predict(models: dict, signal: str, symbol: str):
    import numpy as np
    from datetime import date as today_date

    signal_map = {0: "sell", 1: "hold", 2: "buy"}
    all_probas = []
    latest_date = None

    for key, entry in models.items():
        model = entry["model"]
        features = entry["features"]
        x_latest, date = load_latest_features(features, symbol, signal)
        if x_latest.empty:
            continue
        proba = model.predict_proba(x_latest)
        all_probas.append(proba)
        latest_date = date

    if not all_probas:
        return {
            "signal": "hold",
            "confidence": 0.0,
            "date": latest_date or str(today_date.today()),
        }


def save_prediction(symbol: str, signal: str, confidence: float, position_size: float):
    session = get_session()
    pred = Prediction(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        predicted_signal=signal,
        confidence=confidence,
        position_size=position_size,
    )
    session.add(pred)
    session.commit()
    session.close()


def save_model(model_type, features, signal, symbol, path="models"):
    os.makedirs(path, exist_ok=True)
    key = _feature_key(features)
    model_path = os.path.join(path, f"{symbol}_{signal}_{key}.joblib")
    meta_path = os.path.join(path, f"{symbol}_{signal}_{key}_meta.json")
    model_type.save(model_path)
    with open(meta_path, "w") as f:
        json.dump({"features": features, "signal": signal, "symbol": symbol}, f)
    logger.info(f"Model saved to {model_path}")


def load_trained_model(features, signal, symbol, path="models"):
    key = _feature_key(features)
    model_path = os.path.join(path, f"{symbol}_{signal}_{key}.joblib")
    meta_path = os.path.join(path, f"{symbol}_{signal}_{key}_meta.json")

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        meta = json.load(f)
    if meta["features"] != features or meta["signal"] != signal:
        logger.warning("Saved model mismatch, retraining")
        return None
    model = XGBoostModel()
    model.load(model_path)
    logger.info(f"Model loaded from {model_path}")
    return model


def _feature_key(features):
    return "_".join(f.replace("Features", "").lower() for f in sorted(features))


def walk_forward_grid_search(
    features: list[str],
    signal: str,
    symbol: str,
    param_grid: dict = None,
    train_pct: float = 0.8,
    retrain_every: int = 60,
    min_confidence: float = 0.6,
):
    from backtesting.engine import walk_forward

    if param_grid is None:
        param_grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [4, 5, 6],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.7, 0.8],
        }

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(product(*values))

    logger.info(f"Grid search: {len(combos)} parameter combinations")

    results = []
    for combo in combos:
        params = dict(zip(keys, combo))
        logger.info(f"Testing: {params}")

        def make_model(**p):
            return XGBoostModel(**p)

        wf_result = walk_forward(
            features=features,
            signal=signal,
            symbol=symbol,
            train_pct=train_pct,
            retrain_every=retrain_every,
            min_confidence=min_confidence,
            _model_params=params,
        )

        if wf_result:
            metrics = wf_result["metrics"]
            results.append({"params": params, "metrics": metrics})
            logger.info(
                f"  Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['total_return']}%, Trades: {metrics['total_trades']}"
            )

    if not results:
        logger.warning("No valid results from grid search")
        return None

    best = max(results, key=lambda r: r["metrics"]["sharpe_ratio"])
    logger.info(f"Best params: {best['params']}")
    logger.info(f"Best metrics: {best['metrics']}")

    return {"best_params": best["params"], "all_results": results}
