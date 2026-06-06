import yfinance as yf
import time
import pandas as pd
from src.core.market_data import Candle
from typing import List, Callable, Optional, Awaitable
import asyncio


def fetch_history(
    symbol: str,
    period: str = "1mo",
    interval: str = "1h",
    auto_adjust: bool = True,
) -> pd.DataFrame:

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
    )

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    time_col = "Datetime" if "Datetime" in df.columns else "Date"

    df[time_col] = pd.to_datetime(df[time_col], utc=True)

    df["timestamp"] = df[time_col].apply(lambda x: x.timestamp())

    df["symbol"] = symbol

    return df


def df_to_candles(df: pd.DataFrame):
    return [
        Candle(
            symbol=row.symbol,
            timestamp=float(row.timestamp),
            open=float(row.Open),
            high=float(row.High),
            low=float(row.Low),
            close=float(row.Close),
            volume=float(row.Volume) if "Volume" in df.columns else None,
            source="yfinance",
        )
        for row in df.itertuples(index=False)
    ]


async def stream_history(
    symbols: list[str],
    handler: Callable[[Candle], Awaitable[None] | None],
    period: str = "1mo",
    interval: str = "1h",
    delay: float = 0.0,
):
    for symbol in symbols:
        df = fetch_history(symbol, period=period, interval=interval)

        if df.empty:
            continue

        candles = df_to_candles(df)

        for candle in candles:
            result = handler(candle)

            if hasattr(result, "__await__"):
                await result

            if delay:
                await asyncio.sleep(delay)
