"""Orchestrates data fetch, analysis, report formatting, and prediction logging."""

from __future__ import annotations

from datetime import datetime, timezone

from market.analysis import MarketReport, build_report
from market.data import fetch_ohlcv
from report.formatter import format_candle_close_alert, format_report
from tracking.evaluator import evaluate_pending
from tracking.logger import log_from_report


def generate_report(source: str = "manual") -> tuple[MarketReport, str]:
    """Fetch live data, analyze, log prediction, return report and Telegram HTML text."""
    evaluate_pending()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    daily_df = fetch_ohlcv("1d")
    h4_df = fetch_ohlcv("4h")
    h1_df = fetch_ohlcv("1h")

    report = build_report(daily_df, h4_df, h1_df, now)
    log_from_report(report, source=source)
    text = format_report(report)
    return report, text


def generate_candle_alert(timeframe_key: str) -> str:
    """Generate short alert for a specific timeframe candle close."""
    from config import TIMEFRAMES

    label = TIMEFRAMES[timeframe_key]["label"]
    report, _ = generate_report(source=f"candle_{timeframe_key}")
    return format_candle_close_alert(report, label)
