"""Shared analysis types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

Bias = Literal["long", "short", "wait"]


class Trend(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class TimeframeAnalysis:
    key: str
    label: str
    price: float
    trend: Trend
    rsi: float
    macd_hist: float
    macd_rising: bool
    ema20: float
    ema50: float
    support: float
    resistance: float
    supports: list[float]
    resistances: list[float]
    volume_ratio: float
    is_ranging: bool
    score: int
    notes: list[str] = field(default_factory=list)
