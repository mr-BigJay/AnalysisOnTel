"""Quick multi-timeframe trend status (15m / 1h / 4h)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from market.analysis import analyze_timeframe
from market.data import fetch_ohlcv
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
    """Fetch 15m, 1h, 4h trends for the status menu."""
    from config import STATUS_TIMEFRAMES

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    h4_df = fetch_ohlcv("4h")
    h4 = analyze_timeframe(h4_df, "4h", STATUS_TIMEFRAMES["4h"]["label"])

    h1_df = fetch_ohlcv("1h")
    h1 = analyze_timeframe(
        h1_df, "1h", STATUS_TIMEFRAMES["1h"]["label"], align_with=h4.trend
    )

    m15_df = fetch_ohlcv("15m")
    m15 = analyze_timeframe(
        m15_df, "15m", STATUS_TIMEFRAMES["15m"]["label"], align_with=h1.trend
    )

    timeframes = [
        TimeframeStatus("15m", STATUS_TIMEFRAMES["15m"]["label"], m15.trend, m15.price),
        TimeframeStatus("1h", STATUS_TIMEFRAMES["1h"]["label"], h1.trend, h1.price),
        TimeframeStatus("4h", STATUS_TIMEFRAMES["4h"]["label"], h4.trend, h4.price),
    ]

    return MarketStatus(generated_at=now, price=h1.price, timeframes=timeframes)
