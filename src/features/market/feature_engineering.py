import pandas as pd
import numpy as np
from core.logger_config import logger


def log_returns(df, col="close", periods=(1, 5, 10, 20)):
    for p in periods:
        df[f"log_ret_{p}"] = np.log(df[col] / df[col].shift(p))
    return df


def pct_returns(df, col="close", periods=(1, 5, 10, 20)):
    for p in periods:
        df[f"pct_ret_{p}"] = df[col].pct_change(p)
    return df


def rolling_cumulative_return(df, col="close", window=20):
    df[f"roll_cum_ret_{window}"] = df[col].pct_change().rolling(window).sum()
    return df


def forward_returns(df, col="close", horizons=(1, 5, 10, 20)):
    for h in horizons:
        df[f"fwd_ret_{h}"] = (df[col].shift(-h) / df[col]) - 1
    return df


def rolling_return_stats(df, col="close", window=20):
    r = df[col].pct_change()
    df[f"roll_mean_ret_{window}"] = r.rolling(window).mean()
    df[f"roll_ret_z_{window}"] = (r - r.rolling(window).mean()) / (
        r.rolling(window).std() + 1e-9
    )
    return df


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def momentum_features(df):
    df["rsi_7"] = rsi(df["close"], 7)
    df["rsi_14"] = rsi(df["close"], 14)
    df["rsi_21"] = rsi(df["close"], 21)

    df["ema_10"] = df["close"].ewm(span=10).mean()
    df["ema_20"] = df["close"].ewm(span=20).mean()
    df["ema_50"] = df["close"].ewm(span=50).mean()

    df["ema_dist_20"] = (df["close"] / df["ema_20"]) - 1
    df["ema_dist_10_50"] = df["ema_10"] - df["ema_50"]

    df["rsi_slope"] = df["rsi_14"].diff()
    df["roc_10"] = df["close"].pct_change(10)

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def true_range(df):
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)


def volatility_features(df):
    df["ret"] = df["close"].pct_change()

    for w in [5, 10, 20, 50]:
        df[f"vol_{w}"] = df["ret"].rolling(w).std()

    df["vol_ratio_10_50"] = df["vol_10"] / (df["vol_50"] + 1e-9)

    df["tr"] = true_range(df)
    df["atr_14"] = df["tr"].rolling(14).mean()

    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()

    df["bb_width_20"] = (4 * std) / mid
    df["vol_of_vol"] = df["vol_10"].rolling(10).std()

    return df


def mean_reversion_features(df):
    for w in [10, 20, 50]:
        mean = df["close"].rolling(w).mean()
        std = df["close"].rolling(w).std()

        df[f"zscore_{w}"] = (df["close"] - mean) / (std + 1e-9)

        df[f"dist_mean_{w}"] = df["close"] - mean

    vwap = (df["close"] * df["volume"]).cumsum() / (df["volume"].cumsum() + 1e-9)
    df["vwap_dist"] = (df["close"] / vwap) - 1
    return df


def volume_features(df):
    df["vol_change"] = df["volume"].pct_change()

    df["vol_z_20"] = (df["volume"] - df["volume"].rolling(20).mean()) / (
        df["volume"].rolling(20).std() + 1e-9
    )

    df["obv"] = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()

    df["price_vol_interaction"] = df["ret"] * df["vol_change"]

    return df


def lag_features(df):
    for l in [1, 2, 3, 5, 10]:
        df[f"lag_ret_{l}"] = df["close"].pct_change(l)
        df[f"lag_rsi_{l}"] = rsi(df["close"], 14).shift(l)

    df["autocorr_10"] = (
        df["close"].pct_change().rolling(10).apply(lambda x: x.autocorr())
    )

    return df


def time_features(df):
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.dayofweek

    df["london_session"] = df["hour"].between(7, 16).astype(int)
    df["ny_session"] = df["hour"].between(13, 21).astype(int)

    return df


def build_all_features(df):
    df = log_returns(df)
    df = pct_returns(df)
    df = rolling_cumulative_return(df)
    df = forward_returns(df)
    df = rolling_return_stats(df)

    df = momentum_features(df)
    df = volatility_features(df)
    df = mean_reversion_features(df)
    df = volume_features(df)
    df = lag_features(df)
    df = time_features(df)

    return df.dropna()


def split_features(df):
    return {
        "returns": df[["symbol", "timestamp"] + [c for c in df.columns if "ret" in c]],
        "momentum": df[
            [
                "symbol",
                "timestamp",
                "rsi_7",
                "rsi_14",
                "rsi_21",
                "ema_dist_20",
                "ema_dist_10_50",
                "rsi_slope",
                "macd",
                "macd_signal",
                "macd_hist",
                "roc_10",
            ]
        ],
        "volatility": df[
            ["symbol", "timestamp"]
            + [c for c in df.columns if "vol" in c or "atr" in c]
            + ["bb_width_20"]
        ],
        "mean_reversion": df[
            [
                "symbol",
                "timestamp",
                "zscore_10",
                "zscore_20",
                "zscore_50",
                "vwap_dist",
                "dist_mean_10",
                "dist_mean_20",
                "dist_mean_50",
            ]
        ],
        "volume": df[
            [
                "symbol",
                "timestamp",
                "obv",
                "vol_z_20",
                "vol_change",
                "price_vol_interaction",
            ]
        ],
    }
