from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class MarketDataBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class OHLCV(MarketDataBase, table=True):
    __tablename__ = "ohlcv"
    id: Optional[int] = Field(default=None, primary_key=True)
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    source: Optional[str] = None


class ReturnsFeaturesBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class ReturnsFeatures(ReturnsFeaturesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    log_ret_1: Optional[float] = None
    log_ret_5: Optional[float] = None
    log_ret_10: Optional[float] = None
    log_ret_20: Optional[float] = None

    pct_ret_1: Optional[float] = None
    pct_ret_5: Optional[float] = None
    pct_ret_10: Optional[float] = None
    pct_ret_20: Optional[float] = None

    roll_cum_ret_20: Optional[float] = None
    roll_mean_ret_20: Optional[float] = None
    roll_ret_z_20: Optional[float] = None

    fwd_ret_1: Optional[float] = None
    fwd_ret_5: Optional[float] = None
    fwd_ret_10: Optional[float] = None
    fwd_ret_20: Optional[float] = None


class MomentumFeaturesBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class MomentumFeatures(MomentumFeaturesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    rsi_7: Optional[float] = None
    rsi_14: Optional[float] = None
    rsi_21: Optional[float] = None

    ema_dist_20: Optional[float] = None
    ema_dist_10_50: Optional[float] = None

    rsi_slope: Optional[float] = None
    roc_10: Optional[float] = None

    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None


class VolatilityFeaturesBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class VolatilityFeatures(VolatilityFeaturesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    vol_5: Optional[float] = None
    vol_10: Optional[float] = None
    vol_20: Optional[float] = None

    vol_ratio_10_50: Optional[float] = None
    atr_14: Optional[float] = None
    bb_width_20: Optional[float] = None
    vol_of_vol: Optional[float] = None


class MeanReversionFeaturesBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class MeanReversionFeatures(MeanReversionFeaturesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    zscore_10: Optional[float] = None
    zscore_20: Optional[float] = None
    zscore_50: Optional[float] = None

    dist_mean_10: Optional[float] = None
    dist_mean_20: Optional[float] = None
    dist_mean_50: Optional[float] = None

    vwap_dist: Optional[float] = None


class VolumeFeaturesBase(SQLModel):
    symbol: str = Field(index=True)
    timestamp: datetime = Field(index=True)


class VolumeFeatures(VolumeFeaturesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    vol_change: Optional[float] = None
    vol_z_20: Optional[float] = None
    obv: Optional[float] = None
    price_vol_interaction: Optional[float] = None
