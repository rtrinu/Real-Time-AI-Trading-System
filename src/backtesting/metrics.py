def calc_metrics(df, initial_capital=10_000, trading_days=252):
    returns = df["strategy_return"].dropna()
    equity = df["equity"].dropna()

    total_return = (equity.iloc[-1] / initial_capital) - 1
    ann_return = (1 + total_return) ** (trading_days / len(returns)) - 1
    sharpe = (
        (returns.mean() / returns.std()) * (trading_days**0.5)
        if returns.std() != 0
        else 0
    )

    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    wins = (returns > 0).sum()
    total_trades = df["position_change"].sum()
    win_rate = wins / len(returns) if len(returns) > 0 else 0

    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float("inf")

    return {
        "total_return": round(total_return * 100, 2),
        "annualized_return": round(ann_return * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2),
        "total_trades": int(total_trades),
        "final_equity": round(equity.iloc[-1], 2),
    }
