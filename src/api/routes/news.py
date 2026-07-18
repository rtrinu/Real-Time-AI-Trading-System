from fastapi import APIRouter
from scripts.backfill_news import backfill

router = APIRouter()


@router.post("/backfill/{symbol}/{start_date}/{end_date}")
def trigger_backfill(symbol: str, start_date: str, end_date: str):
    backfill(symbol, start_date, end_date)
    return {"status": "done"}
