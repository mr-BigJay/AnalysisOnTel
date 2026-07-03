"""Orchestrates data fetch, analysis, and report formatting."""

from __future__ import annotations

from datetime import datetime, timezone

from market.analysis import MarketReport, build_report
from market.data import fetch_ohlcv
from report.formatter import format_candle_close_alert, format_report


def generate_report() -> tuple[MarketReport, str]:
    """Fetch live data, analyze, return structured report and Telegram HTML text."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    daily_df = fetch_ohlcv("1d")
    h4_df = fetch_ohlcv("4h")
    h1_df = fetch_ohlcv("1h")

    report = build_report(daily_df, h4_df, h1_df, now)
    text = format_report(report)
    return report, text


def generate_candle_alert(timeframe_key: str) -> str:
    """Generate short alert for a specific timeframe candle close."""
    from config import TIMEFRAMES

    label = TIMEFRAMES[timeframe_key]["label"]
    report, _ = generate_report()
    return format_candle_close_alert(report, label)
