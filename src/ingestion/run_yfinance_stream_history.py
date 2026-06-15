# import asyncio

# from ingestion.adapters.yfinance import stream_history


# async def handler(candle):
#     import pandas as pd

#     readable_time = pd.to_datetime(candle.timestamp, unit="s", utc=True)

#     print(
#         f"{readable_time} | "
#         f"{candle.symbol:<6} | "
#         f"O:{candle.open:<8.2f} "
#         f"H:{candle.high:<8.2f} "
#         f"L:{candle.low:<8.2f} "
#         f"C:{candle.close:<8.2f} "
#         f"V:{candle.volume}"
#     )


# async def main():
#     await stream_history(
#         symbols=["AAPL", "TSLA"],
#         handler=handler,
#         period="5d",
#         interval="1h",
#         delay=0.0,
#     )


# if __name__ == "__main__":
#     asyncio.run(main())
