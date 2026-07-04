"""Simple trend detection for status menu."""

from __future__ import annotations

import pandas as pd

from market.indicators import ema
from market.types import Trend


def detect_trend(df: pd.DataFrame) -> Trend:
    close = df["Close"]
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    c = float(close.iloc[-1])
    e20v = float(e20.iloc[-1])
    e50v = float(e50.iloc[-1])
    if c > e20v > e50v:
        return Trend.BULLISH
    if c < e20v < e50v:
        return Trend.BEARISH
    return Trend.NEUTRAL
