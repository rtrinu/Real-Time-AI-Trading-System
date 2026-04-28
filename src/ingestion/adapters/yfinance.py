import yfinance as yf
import pandas as pd
from typing import Callable, Optional
from core.market_data import MarketTick
from core.adapter.base import BaseMarketAdapter

class YFinanceHistoricalAdapter(BaseMarketAdapter):
    def __init__(self, interval="1m", period="1mo"):
        super().__init__()
        self.interval = interval
        self.period = period
        self.symbols=[]

    async def connect(self):
        self._running = True

    async def subscribe(self, symbols: list[str]):
        self.symbols.extend(symbols)

    def fetch_history(self, symbol: str) -> pd.DataFrame:
        df = yf.download(
            symbol,
            period=self.period,
            interval=self.interval,
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return df

        df = df.reset_index()
        df["symbol"] = symbol
        return df

    async def _stream_loop(self, callback: Callable[[MarketTick], None]):

        for symbol in self.symbols:
            df = self.fetch_history(symbol)

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():

                tick = MarketTick(
                    symbol=symbol,
                    price=float(row["Close"]),
                    volume=float(row["Volume"]) if "Volume" in row else 0,
                    timestamp=row["Datetime"] if "Datetime" in row else row["Date"]
                )

                result = callback(tick)
                if hasattr(result, "__await__"):
                    await result

        self._running = False

    async def disconnect(self):
        self._running = False