import yfinance as yf
import pandas as pd
from db.market_models import OHLCV
from core.logger_config import logger

import yfinance as yf
import pandas as pd


def download_market_data(
    symbol: str = "AAPL", period: str = "1y", interval: str = "1d"
) -> list[dict]:

    logger.info("Downloading OHLCV Data")
    df = yf.download(symbol, period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    df = df.rename(
        columns={
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["symbol"] = symbol

    required_cols = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns from dataframe: {missing}")

    df = df[required_cols]

    records = df.to_dict(orient="records")

    return records
