from transformers import pipeline
import torch


class FinBERTSentiment:
    def __init__(self, model_name="ProsusAI/finbert"):
        device = 0 if torch.cuda.is_available() else -1
        self.classifier = pipeline(
            "sentiment-analysis", model=model_name, device=device, truncation=True
        )

    def predict(self, texts):
        """
        texts: str or list[str]
        returns: list[dict]
        """

        if isinstance(texts, str):
            texts = [texts]

        results = self.classifier(texts, batch_size=64)

        return [
            {"label": r["label"].lower(), "score": float(r["score"])} for r in results
        ]

    def predict_single(self, text: str):
        return self.predict(text)[0]

    def to_score(self, result):
        label = result["label"]
        confidence = float(result["score"])

        if label == "positive":
            sentiment_score = confidence
        elif label == "negative":
            sentiment_score = -confidence
        else:
            sentiment_score = 0.0

        return {
            "sentiment_score": sentiment_score,
            "confidence": confidence,
            "label": label,
        }
