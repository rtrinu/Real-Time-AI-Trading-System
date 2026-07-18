from sklearn.model_selection import train_test_split
from ml.xgboost import XGBoostModel
from training.data_loader import load_training_data
from core.logger_config import logger


def create_split(X, y, test_ratio=0.2):
    x_train, x_test, y_train, y_test = train_test_split(X, y)
    return x_train, x_test, y_train, y_test


def train(model_type, features, signal, symbol):
    X, y = load_training_data(symbol, features, signal)
    x_train, x_test, y_train, y_test = create_split(X, y)
    model_type.train(x_train, y_train)
    evaluate = model_type.evaluate(x_test, y_test)
    logger.info(evaluate)


def save_model(model, model_type, features, signal): ...
