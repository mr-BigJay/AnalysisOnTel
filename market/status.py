"""Quick BTC multi-timeframe status."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from config import STATUS_TIMEFRAMES
from market.data import fetch_ohlcv
from market.trend import detect_trend
from market.types import Trend


@dataclass
class TimeframeStatus:
    key: str
    label: str
    trend: Trend
    price: float


@dataclass
class MarketStatus:
    generated_at: str
    price: float
    timeframes: list[TimeframeStatus]


def fetch_market_status() -> MarketStatus:
    from config import TIMEFRAMES

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    timeframes: list[TimeframeStatus] = []
    price = 0.0

    for key in STATUS_TIMEFRAMES:
        df = fetch_ohlcv(key)
        closed = df.iloc[:-1] if len(df) > 1 else df
        trend = detect_trend(closed)
        p = float(closed["Close"].iloc[-1])
        if key == "1h":
            price = p
        timeframes.append(
            TimeframeStatus(key, TIMEFRAMES[key]["label"], trend, p)
        )

    return MarketStatus(generated_at=now, price=price, timeframes=timeframes)
