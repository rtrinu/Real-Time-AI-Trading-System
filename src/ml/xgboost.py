from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
import joblib


class XGBoostModel:
    def __init__(self):
        self.n_estimators = 200
        self.learning_rate = 0.05
        self.max_depth = 5
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
