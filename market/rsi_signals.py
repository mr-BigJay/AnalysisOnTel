"""RSI extreme zones and divergence detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from market.indicators import rsi


class RsiZone(str, Enum):
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    NEUTRAL = "neutral"


class DivergenceType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class RsiExtreme:
    zone: RsiZone
    rsi_value: float
    price: float
    candle_ts: int


@dataclass
class RsiDivergence:
    kind: DivergenceType
    rsi_value: float
    price: float
    candle_ts: int
    fingerprint: str
    note: str


def current_rsi_zone(
    rsi_value: float,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> RsiZone:
    if rsi_value >= overbought:
        return RsiZone.OVERBOUGHT
    if rsi_value <= oversold:
        return RsiZone.OVERSOLD
    return RsiZone.NEUTRAL


def detect_rsi_extreme(
    df: pd.DataFrame,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> RsiExtreme | None:
    """
    Alert only when RSI crosses into OB/OS on the last *closed* candle.
    Excludes the forming candle to avoid false spikes vs charting apps.
    """
    if len(df) < 17:
        return None

    closed = df.iloc[:-1]
    rsi_series = rsi(closed["Close"])
    if len(rsi_series) < 16:
        return None

    current = float(rsi_series.iloc[-1])
    previous = float(rsi_series.iloc[-2])
    if pd.isna(current) or pd.isna(previous):
        return None

    zone: RsiZone | None = None
    if previous < overbought and current >= overbought:
        zone = RsiZone.OVERBOUGHT
    elif previous > oversold and current <= oversold:
        zone = RsiZone.OVERSOLD

    if zone is None:
        return None

    candle_ts = int(closed.index[-1].timestamp())
    price = float(closed["Close"].iloc[-1])
    return RsiExtreme(zone=zone, rsi_value=round(current, 1), price=price, candle_ts=candle_ts)


def _swing_lows(series: pd.Series, window: int = 3) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    values = series.values
    for i in range(window, len(series) - window):
        segment = values[i - window : i + window + 1]
        if values[i] == segment.min():
            points.append((i, float(values[i])))
    return points


def _swing_highs(series: pd.Series, window: int = 3) -> list[tuple[int, float]]:
    points: list[tuple[int, float]] = []
    values = series.values
    for i in range(window, len(series) - window):
        segment = values[i - window : i + window + 1]
        if values[i] == segment.max():
            points.append((i, float(values[i])))
    return points


def detect_rsi_divergence(
    df: pd.DataFrame,
    lookback: int = 60,
    swing_window: int = 3,
    max_age_bars: int = 12,
    min_rsi_delta: float = 2.0,
) -> RsiDivergence | None:
    """
    Detect classic RSI divergence using the last two swing points.
    Bullish: price lower low + RSI higher low.
    Bearish: price higher high + RSI lower high.
    """
    if len(df) < lookback + 1:
        return None

    # Use closed candles only (drop forming bar)
    segment = df.iloc[:-1].tail(lookback).copy()
    close = segment["Close"]
    rsi_series = rsi(close)
    n = len(segment)

    lows = _swing_lows(close, swing_window)
    highs = _swing_highs(close, swing_window)

    # Bullish divergence
    if len(lows) >= 2:
        i1, p1 = lows[-2]
        i2, p2 = lows[-1]
        if n - 1 - i2 <= max_age_bars and p2 < p1:
            r1 = float(rsi_series.iloc[i1])
            r2 = float(rsi_series.iloc[i2])
            if r2 > r1 + min_rsi_delta:
                ts = int(segment.index[-1].timestamp())
                fp = f"bull_{i1}_{i2}_{p1:.0f}_{p2:.0f}"
                return RsiDivergence(
                    kind=DivergenceType.BULLISH,
                    rsi_value=round(r2, 1),
                    price=float(close.iloc[-1]),
                    candle_ts=ts,
                    fingerprint=fp,
                    note=f"قیمت کف پایین‌تر ({p1:,.0f}→{p2:,.0f}) ولی RSI کف بالاتر ({r1:.0f}→{r2:.0f})",
                )

    # Bearish divergence
    if len(highs) >= 2:
        i1, p1 = highs[-2]
        i2, p2 = highs[-1]
        if n - 1 - i2 <= max_age_bars and p2 > p1:
            r1 = float(rsi_series.iloc[i1])
            r2 = float(rsi_series.iloc[i2])
            if r2 < r1 - min_rsi_delta:
                ts = int(segment.index[-1].timestamp())
                fp = f"bear_{i1}_{i2}_{p1:.0f}_{p2:.0f}"
                return RsiDivergence(
                    kind=DivergenceType.BEARISH,
                    rsi_value=round(r2, 1),
                    price=float(close.iloc[-1]),
                    candle_ts=ts,
                    fingerprint=fp,
                    note=f"قیمت سقف بالاتر ({p1:,.0f}→{p2:,.0f}) ولی RSI سقف پایین‌تر ({r1:.0f}→{r2:.0f})",
                )

    return None
