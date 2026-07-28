from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/portfolio")
def portfolio(request: Request):
    client = getattr(request.app.state, "alpaca_client", None)
    if not client:
        raise HTTPException(status_code=503, detail="Alpaca client not initialized")

    try:
        account = client.get_account()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch account: {e}")

    try:
        positions = client.get_all_positions()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch positions: {e}")

    equity = float(account.equity)
    last_equity = float(getattr(account, "last_equity", "0"))

    return {
        "account": {
            "equity": equity,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "day_trade_count": account.daytrade_count,
            "today_pnl": round(equity - last_equity, 2),
        },
        "positions": [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "market_value": float(p.market_value),
                "cost_basis": float(p.cost_basis),
                "unrealized_pnl": float(p.unrealized_pl),
                "unrealized_pnl_pct": round(float(p.unrealized_plpc) * 100, 2),
                "current_price": float(p.current_price),
                "side": "long" if float(p.qty) > 0 else "short",
            }
            for p in positions
        ],
    }
