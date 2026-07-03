"""Historical backtest engine."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import DATA_DIR
from market.analysis import MarketReport, TradeScenario, build_report
from market.data import fetch_ohlcv
from market.derivatives import DerivativesSnapshot

logger = logging.getLogger(__name__)

BACKTEST_RESULT_FILE = DATA_DIR / "backtest_last.json"
NEUTRAL_DERIVATIVES = DerivativesSnapshot(
    funding_rate=0.0,
    open_interest_usd=None,
    long_short_ratio=1.0,
    fear_greed_value=50,
    fear_greed_label="Neutral",
    source_notes=["backtest-neutral"],
)


@dataclass
class BacktestTrade:
    time: str
    bias: str
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profit: float
    outcome: str
    outcome_price: float | None
    note: str


@dataclass
class BacktestResult:
    run_at: str
    candles_tested: int
    signals: int
    wins: int
    losses: int
    no_entry: int
    inconclusive: int
    win_rate: float | None
    profit_factor: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _simulate_trade(scenario: TradeScenario, forward: pd.DataFrame) -> tuple[str, float | None, str]:
    entered = False
    entry_low = scenario.entry_low
    entry_high = scenario.entry_high
    sl = scenario.stop_loss
    tp = scenario.take_profit

    for candle in forward.itertuples():
        low = float(candle.Low)
        high = float(candle.High)
        if not entered:
            if low <= entry_high and high >= entry_low:
                entered = True
        if not entered:
            continue
        if scenario.bias == "long":
            if low <= sl:
                return "loss", sl, "SL hit"
            if high >= tp:
                return "win", tp, "TP hit"
        else:
            if high >= sl:
                return "loss", sl, "SL hit"
            if low <= tp:
                return "win", tp, "TP hit"

    if not entered:
        return "no_entry", float(forward["Close"].iloc[-1]), "No entry touch"

    last = float(forward["Close"].iloc[-1])
    return "inconclusive", last, "Open at window end"


def run_backtest(h4_candles: int = 180) -> BacktestResult:
    """Walk-forward backtest on 4H candles using current strategy rules."""
    daily = fetch_ohlcv("1d", candles=120)
    h4 = fetch_ohlcv("4h", candles=min(720, h4_candles))
    h1 = fetch_ohlcv("1h", candles=720)

    trades: list[BacktestTrade] = []
    forward_bars = 12  # 48 hours on 4H

    start_idx = 50
    for i in range(start_idx, len(h4) - forward_bars):
        ts = h4.index[i]
        daily_slice = daily[daily.index <= ts]
        h4_slice = h4.iloc[: i + 1]
        h1_slice = h1[h1.index <= ts]
        if len(daily_slice) < 25 or len(h4_slice) < 25 or len(h1_slice) < 25:
            continue

        report: MarketReport = build_report(
            daily_slice,
            h4_slice,
            h1_slice,
            str(ts),
            derivatives=NEUTRAL_DERIVATIVES,
            check_events=False,
        )
        if report.action != "full" or not report.scenario:
            continue

        forward = h4.iloc[i + 1 : i + 1 + forward_bars]
        outcome, price, note = _simulate_trade(report.scenario, forward)
        trades.append(
            BacktestTrade(
                time=str(ts),
                bias=report.scenario.bias,
                entry_low=report.scenario.entry_low,
                entry_high=report.scenario.entry_high,
                stop_loss=report.scenario.stop_loss,
                take_profit=report.scenario.take_profit,
                outcome=outcome,
                outcome_price=price,
                note=note,
            )
        )

    wins = sum(1 for t in trades if t.outcome == "win")
    losses = sum(1 for t in trades if t.outcome == "loss")
    no_entry = sum(1 for t in trades if t.outcome == "no_entry")
    inconclusive = sum(1 for t in trades if t.outcome == "inconclusive")
    decided = wins + losses
    win_rate = (wins / decided * 100) if decided else None

    gross_win = wins
    gross_loss = losses
    profit_factor = (gross_win / gross_loss) if gross_loss else None

    result = BacktestResult(
        run_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        candles_tested=len(h4) - start_idx - forward_bars,
        signals=len(trades),
        wins=wins,
        losses=losses,
        no_entry=no_entry,
        inconclusive=inconclusive,
        win_rate=win_rate,
        profit_factor=profit_factor,
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST_RESULT_FILE.write_text(
        json.dumps({"result": result.to_dict(), "trades": [asdict(t) for t in trades[-10:]]}, indent=2),
        encoding="utf-8",
    )
    logger.info("Backtest done: %s signals, win_rate=%s", len(trades), win_rate)
    return result
