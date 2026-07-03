"""Log predictions from market reports."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from config import PREDICTION_EVAL_HOURS, PREDICTION_LOG_COOLDOWN_MIN
from market.analysis import MarketReport
from tracking.database import get_recent_duplicate, insert_prediction, utc_now_iso

logger = logging.getLogger(__name__)


def _eval_after_iso(hours: int | None = None) -> str:
    h = hours if hours is not None else PREDICTION_EVAL_HOURS
    dt = datetime.now(timezone.utc) + timedelta(hours=h)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _should_log(report: MarketReport) -> bool:
    """Log when there is a directional view or trade scenario."""
    if report.allowed_bias == "wait" and report.action in ("wait", "no_signal"):
        return False
    return True


def log_from_report(report: MarketReport, source: str) -> int | None:
    """
    Save prediction snapshot. Returns new row id or None if skipped.
    """
    if not _should_log(report):
        return None

    bias = report.allowed_bias if report.allowed_bias != "wait" else (
        report.scenario.bias if report.scenario else "wait"
    )
    if bias == "wait":
        return None

    if get_recent_duplicate(bias, report.action, PREDICTION_LOG_COOLDOWN_MIN):
        logger.debug("Skip duplicate prediction log (%s/%s)", bias, report.action)
        return None

    scenario = report.scenario
    note = (
        f"Daily={report.daily.trend.value}; 4H={report.h4.trend.value}; "
        f"1H={report.h1.trend.value}; action={report.action}"
    )

    row_id = insert_prediction(
        source=source,
        symbol=report.symbol,
        bias=bias,
        action=report.action,
        price_at_signal=report.h1.price,
        eval_after=_eval_after_iso(),
        entry_low=scenario.entry_low if scenario else None,
        entry_high=scenario.entry_high if scenario else None,
        stop_loss=scenario.stop_loss if scenario else None,
        take_profit=scenario.take_profit if scenario else None,
        confidence=scenario.confidence if scenario else None,
        quality_score=report.quality_score,
        checklist_score=report.checklist.score,
        daily_trend=report.daily.trend.value,
        h4_trend=report.h4.trend.value,
        h1_trend=report.h1.trend.value,
        prediction_note=note,
    )
    logger.info("Logged prediction #%s source=%s bias=%s action=%s", row_id, source, bias, report.action)
    return row_id
