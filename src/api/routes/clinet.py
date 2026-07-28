from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/portfolio")
def portfolio(request: Request):
    client = request.app.state.alpaca_client
    account = client.get_account()
    positions = client.get_all_positions()

    return {
        "account": {
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "day_trade_count": account.daytrade_count,
            "today_pnl": float(account.equity) - float(account.last_equity),
        },
        "positions": [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "market_value": float(p.market_value),
                "cost_basis": float(p.cost_basis),
                "unrealized_pnl": float(p.unrealized_pl),
                "unrealized_pnl_pct": float(p.unrealized_plpc) * 100,
                "current_price": float(p.current_price),
                "side": "long" if float(p.qty) > 0 else "short",
            }
            for p in positions
        ],
    }
