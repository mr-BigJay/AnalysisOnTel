"""Persist report snapshots for diff and entry-zone monitoring."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import DATA_DIR
from market.analysis import MarketReport

logger = logging.getLogger(__name__)

LAST_REPORT_PATH = DATA_DIR / "last_report.json"
ACTIVE_SCENARIO_PATH = DATA_DIR / "active_scenario.json"


def _report_to_dict(report: MarketReport) -> dict:
    scenario = None
    if report.scenario:
        s = report.scenario
        scenario = {
            "bias": s.bias,
            "entry_low": s.entry_low,
            "entry_high": s.entry_high,
            "stop_loss": s.stop_loss,
            "take_profit": s.take_profit,
            "confidence": s.confidence,
        }

    return {
        "generated_at": report.generated_at,
        "price": report.h1.price,
        "daily_trend": report.daily.trend.value,
        "h4_trend": report.h4.trend.value,
        "h1_trend": report.h1.trend.value,
        "action": report.action,
        "quality_score": report.quality_score,
        "checklist_score": report.checklist.score,
        "checklist_passed": report.checklist.passed,
        "scenario": scenario,
    }


def load_last_report() -> dict | None:
    if not LAST_REPORT_PATH.exists():
        return None
    try:
        return json.loads(LAST_REPORT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load last report snapshot")
        return None


def save_last_report(report: MarketReport) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_REPORT_PATH.write_text(
        json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scenario_fingerprint(scenario: dict) -> str:
    return (
        f"{scenario['bias']}_{scenario['entry_low']:.0f}"
        f"_{scenario['entry_high']:.0f}_{scenario['stop_loss']:.0f}"
    )


def save_active_scenario(report: MarketReport) -> None:
    """Store entry zone for price watcher when action is full."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if report.action != "full" or not report.scenario:
        if ACTIVE_SCENARIO_PATH.exists():
            ACTIVE_SCENARIO_PATH.unlink()
        return

    s = report.scenario
    scenario_dict = {
        "bias": s.bias,
        "entry_low": s.entry_low,
        "entry_high": s.entry_high,
        "stop_loss": s.stop_loss,
        "take_profit": s.take_profit,
        "confidence": s.confidence,
        "saved_at": report.generated_at,
    }
    fp = scenario_fingerprint(scenario_dict)

    alerted = False
    if ACTIVE_SCENARIO_PATH.exists():
        try:
            prev = json.loads(ACTIVE_SCENARIO_PATH.read_text(encoding="utf-8"))
            if prev.get("fingerprint") == fp:
                alerted = bool(prev.get("alerted", False))
        except (json.JSONDecodeError, OSError):
            pass

    payload = {**scenario_dict, "fingerprint": fp, "alerted": alerted}
    ACTIVE_SCENARIO_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_active_scenario() -> dict | None:
    if not ACTIVE_SCENARIO_PATH.exists():
        return None
    try:
        return json.loads(ACTIVE_SCENARIO_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def mark_scenario_alerted() -> None:
    data = load_active_scenario()
    if not data:
        return
    data["alerted"] = True
    ACTIVE_SCENARIO_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_active_scenario() -> None:
    if ACTIVE_SCENARIO_PATH.exists():
        ACTIVE_SCENARIO_PATH.unlink()
