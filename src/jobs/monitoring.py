from datetime import datetime, timezone, timedelta, time
from db.create_engine import get_session
from db.prediction_models import Prediction
from db.market_models import OHLCV
from sqlmodel import select, col
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.logger_config import logger


def evaluate_predictions():
    try:
        session = get_session()
        today = datetime.now(timezone.utc)
        cutoff = today - timedelta(days=7)

        unevaluated = session.exec(
            select(Prediction).where(
                Prediction.timestamp <= cutoff, Prediction.actual_signal == None
            )
        ).all()

        logger.info(f"Evaluating {len(unevaluated)} predictions")

        for pred in unevaluated:
            try:
                pred_date = pred.timestamp.date()
                pred_close = session.exec(
                    select(OHLCV.close).where(
                        OHLCV.symbol == pred.symbol,
                        OHLCV.timestamp >= datetime.combine(pred_date, time.min),
                        OHLCV.timestamp <= datetime.combine(pred_date, time.max),
                    )
                ).first()

                eval_date = (pred.timestamp + timedelta(days=7)).date()
                eval_close = session.exec(
                    select(OHLCV.close)
                    .where(
                        OHLCV.symbol == pred.symbol,
                        OHLCV.timestamp <= datetime.combine(eval_date, time.max),
                    )
                    .order_by(OHLCV.timestamp.desc())
                    .limit(1)
                ).first()

                if not pred_close or not eval_close:
                    continue

                actual_return = (eval_close - pred_close) / pred_close
                if actual_return > 0.02:
                    actual_signal = "buy"
                elif actual_return < -0.02:
                    actual_signal = "sell"
                else:
                    actual_signal = "hold"

                pred.actual_signal = actual_signal
                pred.actual_return = actual_return
                pred.is_correct = pred.predicted_signal == actual_signal
                pred.evaluated_at = datetime.now()

                session.add(pred)
                logger.info(
                    f"Evaluated {pred.symbol}: predicted={pred.predicted_signal}, actual={actual_signal}, correct={pred.is_correct}"
                )
            except Exception as e:
                logger.error(f"Failed to evaluate prediction {pred.id}: {e}")
                continue

        session.commit()

        for window in [20, 50, 100]:
            recent = session.exec(
                select(Prediction)
                .where(Prediction.is_correct != None)
                .order_by(col(Prediction.evaluated_at).desc())
                .limit(window)
            ).all()
            accuracy = (
                sum(1 for p in recent if p.is_correct) / len(recent) if recent else 0
            )
            logger.info(f"Accuracy (last {window}): {accuracy:.1%}")
    except Exception as e:
        logger.error(f"Prediction evaluation failed: {e}")


monitoring_scheduler = AsyncIOScheduler()


def start_monitoring_scheduler(app):
    monitoring_scheduler.add_job(
        evaluate_predictions,
        CronTrigger(hour=17, minute=30, timezone="US/Eastern"),
        id="monitoring",
        replace_existing=True,
    )
    monitoring_scheduler.start()
