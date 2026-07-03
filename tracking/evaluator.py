"""Evaluate pending predictions against market outcomes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from market.data import fetch_ohlcv
from tracking.database import PredictionRow, fetch_pending_for_eval, update_outcome

logger = logging.getLogger(__name__)


def evaluate_pending() -> int:
    """Evaluate all due predictions. Returns count updated."""
    pending = fetch_pending_for_eval()
    updated = 0
    for row in pending:
        try:
            outcome, price, note = _evaluate_row(row)
            update_outcome(row.id, outcome, price, note)
            updated += 1
            logger.info("Prediction #%s outcome=%s (%s)", row.id, outcome, note)
        except Exception:
            logger.exception("Failed to evaluate prediction #%s", row.id)
    return updated


def _evaluate_row(row: PredictionRow) -> tuple[str, float | None, str]:
    df = fetch_ohlcv("1h")
    created = pd.Timestamp(row.created_at, tz="UTC")
    candles = df[df.index >= created]
    if candles.empty:
        return "inconclusive", row.price_at_signal, "داده کافی برای ارزیابی نیست"

    last_price = float(candles["Close"].iloc[-1])

    if row.bias not in ("long", "short") or row.stop_loss is None or row.take_profit is None:
        return _evaluate_directional(row, candles, last_price)

    if row.entry_low is None or row.entry_high is None:
        return _evaluate_directional(row, candles, last_price)

    if row.bias == "long":
        return _evaluate_trade_long(row, candles, last_price)
    return _evaluate_trade_short(row, candles, last_price)


def _evaluate_directional(
    row: PredictionRow, candles: pd.DataFrame, last_price: float
) -> tuple[str, float | None, str]:
    start = row.price_at_signal
    if row.bias == "long":
        if last_price > start * 1.002:
            return "win", last_price, "قیمت بالاتر از زمان پیش‌بینی (جهت صعودی درست)"
        if last_price < start * 0.998:
            return "loss", last_price, "قیمت پایین‌تر از زمان پیش‌بینی (جهت نادرست)"
        return "inconclusive", last_price, "حرکت محدود — نتیجه نامشخص"
    if row.bias == "short":
        if last_price < start * 0.998:
            return "win", last_price, "قیمت پایین‌تر از زمان پیش‌بینی (جهت نزولی درست)"
        if last_price > start * 1.002:
            return "loss", last_price, "قیمت بالاتر از زمان پیش‌بینی (جهت نادرست)"
        return "inconclusive", last_price, "حرکت محدود — نتیجه نامشخص"
    return "inconclusive", last_price, "bias خنثی"


def _evaluate_trade_long(
    row: PredictionRow, candles: pd.DataFrame, last_price: float
) -> tuple[str, float | None, str]:
    sl = float(row.stop_loss)
    tp = float(row.take_profit)
    entry_low = float(row.entry_low)
    entry_high = float(row.entry_high)
    entered = False

    for candle in candles.itertuples():
        low = float(candle.Low)
        high = float(candle.High)
        if not entered:
            if low <= entry_high and high >= entry_low:
                entered = True
        if not entered:
            continue
        if low <= sl:
            return "loss", sl, "حد ضرر لانگ فعال شد"
        if high >= tp:
            return "win", tp, "هدف سود لانگ برخورد شد"

    if not entered:
        return "no_entry", last_price, "قیمت به ناحیه ورود نرسید"

    pnl_pct = ((last_price - row.price_at_signal) / row.price_at_signal) * 100
    if pnl_pct >= 0.3:
        return "win", last_price, f"ورود انجام شد؛ سود جزئی +{pnl_pct:.2f}%"
    if pnl_pct <= -0.3:
        return "loss", last_price, f"ورود انجام شد؛ ضرر جزئی {pnl_pct:.2f}%"
    return "inconclusive", last_price, "ورود انجام شد؛ نتیجه هنوز نامشخص"


def _evaluate_trade_short(
    row: PredictionRow, candles: pd.DataFrame, last_price: float
) -> tuple[str, float | None, str]:
    sl = float(row.stop_loss)
    tp = float(row.take_profit)
    entry_low = float(row.entry_low)
    entry_high = float(row.entry_high)
    entered = False

    for candle in candles.itertuples():
        low = float(candle.Low)
        high = float(candle.High)
        if not entered:
            if low <= entry_high and high >= entry_low:
                entered = True
        if not entered:
            continue
        if high >= sl:
            return "loss", sl, "حد ضرر شورت فعال شد"
        if low <= tp:
            return "win", tp, "هدف سود شورت برخورد شد"

    if not entered:
        return "no_entry", last_price, "قیمت به ناحیه ورود نرسید"

    pnl_pct = ((row.price_at_signal - last_price) / row.price_at_signal) * 100
    if pnl_pct >= 0.3:
        return "win", last_price, f"ورود انجام شد؛ سود جزئی +{pnl_pct:.2f}%"
    if pnl_pct <= -0.3:
        return "loss", last_price, f"ورود انجام شد؛ ضرر جزئی {pnl_pct:.2f}%"
    return "inconclusive", last_price, "ورود انجام شد؛ نتیجه هنوز نامشخص"
