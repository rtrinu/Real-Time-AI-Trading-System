from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
import joblib


class XGBoostModel:
    def __init__(self):
        n_estimators = (200,)
        learning_rate = 0.05
        max_depth = 5
        subsample = 0.8
        colsample_bytree = 0.8
        random_state = 42
        n_jobs = 1
        model = XGBClassifier(
            self.n_estimators,
            self.learning_rate,
            self.max_depth,
            self.subsample,
            self.colsample_bytree,
            self.random_state,
            self.n_jobs,
        )

    def train(self, x_train, y_train):
        self.model.fit(x_train, y_train)

    def predict(self, x):
        return self.model.predict(x)

    def predict_proba(self, x):
        return self.model.predict_proba(x)

    def evaluate(self, x_test, y_test):
        predictions = self.predict(x_test)
        return accuracy_score(y_test, predictions)

    def save(self, path):
        joblib.dump(self.model, path)

    def load(self, path):
        self.model = joblib.load(path)
