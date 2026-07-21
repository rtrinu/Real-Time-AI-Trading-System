from sklearn.model_selection import train_test_split
from ml.xgboost import XGBoostModel
from training.data_loader import load_training_data, load_latest_features
from core.logger_config import logger


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


def save_model(model, model_type, features, signal): ...
