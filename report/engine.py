"""Orchestrates data fetch, analysis, report formatting, and prediction logging."""

from __future__ import annotations

from datetime import datetime, timezone

from market.analysis import MarketReport, build_report
from market.data import fetch_ohlcv
from market.institutional import build_institutional_brief
from report.diff import format_report_diff
from report.formatter import format_candle_close_alert
from report.institutional_formatter import format_institutional_report
from report.snapshot import load_last_report, save_active_scenario, save_last_report
from tracking.evaluator import evaluate_pending
from tracking.logger import log_from_report
from tracking.tuning import auto_tune


def _build_live_report() -> tuple[MarketReport, object, object, object]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    daily_df = fetch_ohlcv("1d")
    h4_df = fetch_ohlcv("4h")
    h1_df = fetch_ohlcv("1h")
    report = build_report(daily_df, h4_df, h1_df, now)
    return report, daily_df, h4_df, h1_df


def generate_report(
    source: str = "manual",
    *,
    log_prediction: bool = True,
    include_diff: bool = True,
) -> tuple[MarketReport, str | list[str]]:
    """Fetch live data, analyze, optionally log prediction, return report and Telegram HTML."""
    evaluate_pending()
    auto_tune()

    previous = load_last_report() if include_diff else None
    report, daily_df, h4_df, h1_df = _build_live_report()

    if log_prediction:
        log_from_report(report, source=source)

    save_active_scenario(report)
    brief = build_institutional_brief(report, daily_df, h4_df, h1_df, previous)
    diff_block = format_report_diff(report, previous) if include_diff else None
    messages = format_institutional_report(report, brief, diff_block=diff_block)
    save_last_report(report)

    # CLI / single-message callers get part 1 only; Telegram bot sends all parts
    text: str | list[str] = messages if len(messages) > 1 else messages[0]
    return report, text


def generate_report_messages(
    source: str = "manual",
    *,
    log_prediction: bool = True,
    include_diff: bool = True,
) -> tuple[MarketReport, list[str]]:
    """Always return a list of Telegram HTML message parts."""
    report, text = generate_report(
        source=source,
        log_prediction=log_prediction,
        include_diff=include_diff,
    )
    if isinstance(text, list):
        return report, text
    return report, [text]


def generate_candle_alert(timeframe_key: str) -> str | None:
    """Generate short alert for a specific timeframe candle close (full action only)."""
    from config import TIMEFRAMES

    label = TIMEFRAMES[timeframe_key]["label"]
    report, _, _, _ = _build_live_report()

    if report.action != "full":
        return None

    return format_candle_close_alert(report, label)
