"""Orchestrates data fetch, analysis, report formatting, and prediction logging."""

from __future__ import annotations

from datetime import datetime, timezone

from market.analysis import MarketReport, build_report
from market.data import fetch_ohlcv
from report.diff import format_report_diff
from report.formatter import format_candle_close_alert, format_report
from report.snapshot import load_last_report, save_active_scenario, save_last_report
from tracking.evaluator import evaluate_pending
from tracking.logger import log_from_report
from tracking.tuning import auto_tune


def _build_live_report() -> MarketReport:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    daily_df = fetch_ohlcv("1d")
    h4_df = fetch_ohlcv("4h")
    h1_df = fetch_ohlcv("1h")
    return build_report(daily_df, h4_df, h1_df, now)


def generate_report(
    source: str = "manual",
    *,
    log_prediction: bool = True,
    include_diff: bool = True,
) -> tuple[MarketReport, str]:
    """Fetch live data, analyze, optionally log prediction, return report and Telegram HTML text."""
    evaluate_pending()
    auto_tune()

    previous = load_last_report() if include_diff else None
    report = _build_live_report()

    if log_prediction:
        log_from_report(report, source=source)

    save_active_scenario(report)
    diff_block = format_report_diff(report, previous) if include_diff else None
    text = format_report(report, diff_block=diff_block)
    save_last_report(report)
    return report, text


def generate_candle_alert(timeframe_key: str) -> str | None:
    """Generate short alert for a specific timeframe candle close (full action only)."""
    from config import TIMEFRAMES

    label = TIMEFRAMES[timeframe_key]["label"]
    report = _build_live_report()

    if report.action != "full":
        return None

    return format_candle_close_alert(report, label)
