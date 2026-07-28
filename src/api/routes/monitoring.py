from fastapi import APIRouter, Request
from db.create_engine import get_session
from db.prediction_models import Prediction
from sqlmodel import select, col

from pydantic import BaseModel


router = APIRouter()


@router.get("/monitoring/accuracy")
def get_accuracy():
    session = get_session()
    total = session.exec(select(Prediction).where(Prediction.is_correct != None)).all()

    def rolling_accuracy(n):
        recent = session.exec(
            select(Prediction)
            .where(Prediction.is_correct != None)
            .order_by(col(Prediction.evaluated_at).desc())
            .limit(n)
        ).all()
        return (
            round(sum(1 for p in recent if p.is_correct) / len(recent), 2)
            if recent
            else 0
        )

    by_signal = {}
    for signal in ["buy", "sell", "hold"]:
        preds = [p for p in total if p.predicted_signal == signal]
        correct = sum(1 for p in preds if p.is_correct)
        by_signal[signal] = {
            "count": len(preds),
            "accuracy": round(correct / len(preds), 2) if preds else 0,
        }

    return {
        "total_predictions": len(total),
        "accuracy_20": rolling_accuracy(20),
        "accuracy_50": rolling_accuracy(50),
        "accuracy_100": rolling_accuracy(100),
        "by_signal": by_signal,
    }


@router.get("/monitoring/predictions")
def get_predictions(limit: int = 50):
    session = get_session()

    preds = session.exec(
        select(Prediction).order_by(col(Prediction.timestamp).desc()).limit(limit)
    ).all()

    return [
        {
            "symbol": p.symbol,
            "timestamp": str(p.timestamp),
            "predicted_signal": p.predicted_signal,
            "confidence": p.confidence,
            "position_size": p.position_size,
            "actual_signal": p.actual_signal,
            "actual_return": (
                round(p.actual_return * 100, 2) if p.actual_return else None
            ),
            "is_correct": p.is_correct,
        }
        for p in preds
    ]

@router.get("/monitoring/recent")
def monitoring_recent(limit: int = 5):
    session = get_session()

    def rolling_accuracy(n):
        recent = session.exec(
            select(Prediction)
            .where(Prediction.is_correct != None)
            .order_by(col(Prediction.evaluated_at).desc())
            .limit(n)
        ).all()
        return (
            round(sum(1 for p in recent if p.is_correct) / len(recent), 2)
            if recent
            else 0
        )

    last_trade = session.exec(
        select(Prediction).order_by(col(Prediction.timestamp).desc()).limit(1)
    ).first()

    recent = session.exec(
        select(Prediction)
        .where(Prediction.is_correct != None)
        .order_by(col(Prediction.timestamp).desc())
        .limit(limit)
    ).all()

    total = session.exec(select(Prediction)).all()
    evaluated = [p for p in total if p.is_correct is not None]

    return {
        "last_trade": {
            "symbol": last_trade.symbol,
            "timestamp": str(last_trade.timestamp),
            "signal": last_trade.predicted_signal,
            "confidence": last_trade.confidence,
            "position_size": last_trade.position_size,
            "actual_signal": last_trade.actual_signal,
            "actual_return": (
                round(last_trade.actual_return * 100, 2) if last_trade.actual_return else None
            ),
            "is_correct": last_trade.is_correct,
        } if last_trade else None,
        "evaluation_summary": {
            "total_predictions": len(total),
            "evaluated": len(evaluated),
            "accuracy_last_20": rolling_accuracy(20),
            "recent_trades": [
                {
                    "date": str(p.timestamp.date()),
                    "predicted": p.predicted_signal,
                    "actual": p.actual_signal,
                    "correct": p.is_correct,
                    "return": round(p.actual_return * 100, 2) if p.actual_return else None,
                }
                for p in recent
            ],
        },
    }