from fastapi import APIRouter
from backtesting.engine import VectorisedBacktest
from pydantic import BaseModel
from backtesting.visualisation import save_all_charts

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str = "AAPL"
    signal: str = "signal_5"
    features: list[str] = ["ReturnsFeatures", "Sentiment"]
    initial_capital: float = 10_000
    transaction_cost: float = 0.001
    min_confidence: float = 0.6
    save_charts: bool = True


@router.post("/backtest")
def run_backtest(request: BacktestRequest, req: Request):
    model = req.app.state.model
    bt = VectorisedBacktest(
        model=model,
        symbol=request.symbol,
        features=request.features,
        signal=request.signal,
        initial_capital=request.initial_capital,
        transaction_cost=request.transaction_cost,
        min_confidence=request.min_confidence,
        save_charts=request.save_charts,
    )
    result = bt.run()
    return {
        "metrics": results["metrics"],
        "chart_paths": results.get("chart_paths"),
    }
