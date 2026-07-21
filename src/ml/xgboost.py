from xgboost import XGBClassifier
from sklearn.metrics import classification_report
import joblib
from collections import Counter
import numpy as np


class XGBoostModel:
    def __init__(self):
        self.n_estimators = 50
        self.learning_rate = 0.05
        self.max_depth = 3
        self.subsample = 0.8
        self.colsample_bytree = 0.8
        self.random_state = 42
        self.n_jobs = 1
        self.model = XGBClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )

    def train(self, x_train, y_train, x_val=None, y_val=None):
        counts = Counter(y_train)
        total = len(y_train)
        n_classes = len(counts)
        weights = {cls: total / (n_classes * count) for cls, count in counts.items()}
        sample_weight = np.array([weights[label] for label in y_train])

        fit_params = {"sample_weight": sample_weight}
        if x_val is not None:
            fit_params["eval_set"] = [(x_val, y_val)]
            fit_params["verbose"] = False
        self.model.fit(x_train, y_train, **fit_params)

    def predict(self, x):
        return self.model.predict(x)

    def predict_proba(self, x):
        return self.model.predict_proba(x)

    def evaluate(self, x_test, y_test):
        predictions = self.predict(x_test)
        return classification_report(
            y_test, predictions, target_names=["sell", "hold", "buy"]
        )

    def save(self, path):
        joblib.dump(self.model, path)

    def load(self, path):
        self.model = joblib.load(path)
