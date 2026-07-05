"""Report data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TradeSetup:
    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    risk_reward: float
    leverage: int
    style: str  # Scalp | Intraday | Swing | Position
    invalidation: str
    reason: str


@dataclass
class InstitutionalReport:
    generated_at: str
    price: float
    bias: str  # Bullish | Bearish | Neutral
    stars: int  # 1-5
    confidence: int  # 0-100
    bullish_pct: int
    bearish_pct: int
    verdict: str  # LONG | SHORT | WAIT | NO TRADE
    liquidity: dict[str, Any]
    structure: dict[str, Any]
    ict: dict[str, Any]
    wyckoff: dict[str, Any]
    orderflow: dict[str, Any]
    macro: dict[str, Any]
    confirmations: dict[str, bool]
    confirmation_count: int
    trade: TradeSetup | None
    narrative: str
    sections: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.trade:
            d["trade"] = asdict(self.trade)
        return d
