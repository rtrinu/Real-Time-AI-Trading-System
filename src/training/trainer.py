from sklearn.model_selection import train_test_split
from ml.xgboost import XGBoostModel
from training.data_loader import load_training_data, load_latest_features
from core.logger_config import logger
import os
import json


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

    signal_map = {0: "sell", 1: "hold", 2: "buy"}
    all_probas = []

    for key, entry in models.items():
        model = entry["model"]
        features = entry["features"]
        x_latest, date = load_latest_features(features, symbol, signal)
        if x_latest.empty:
            continue
        proba = model.predict_proba(x_latest)
        all_probas.append(proba)

    if not all_probas:
        return {"signal": "hold", "confidence": 0.0, "date": date}

    avg_probas = np.mean(all_probas, axis=0)
    prediction = int(np.argmax(avg_probas))
    confidence = float(np.max(avg_probas))

    return {
        "signal": signal_map[prediction],
        "confidence": confidence,
        "date": date,
    }


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
