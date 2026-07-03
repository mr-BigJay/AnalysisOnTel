"""Monitor BTC price for entry-zone hits."""

from __future__ import annotations

import logging

from market.data import fetch_ohlcv
from report.snapshot import (
    clear_active_scenario,
    load_active_scenario,
    mark_scenario_alerted,
)

logger = logging.getLogger(__name__)


def _current_price() -> float:
    df = fetch_ohlcv("1h", candles=2)
    return float(df["Close"].iloc[-1])


def _is_in_entry_zone(price: float, entry_low: float, entry_high: float) -> bool:
    return entry_low <= price <= entry_high


def _is_invalidated(price: float, scenario: dict) -> bool:
    bias = scenario["bias"]
    sl = scenario["stop_loss"]
    if bias == "long" and price < sl:
        return True
    if bias == "short" and price > sl:
        return True
    return False


def check_entry_zone() -> str | None:
    """
    Check if price entered the active entry zone.
    Returns Telegram HTML alert text, or None if no alert needed.
    """
    scenario = load_active_scenario()
    if not scenario or scenario.get("alerted"):
        return None

    try:
        price = _current_price()
    except Exception:
        logger.exception("Failed to fetch price for entry watcher")
        return None

    if _is_invalidated(price, scenario):
        logger.info("Active scenario invalidated at price %s", price)
        clear_active_scenario()
        return None

    entry_low = scenario["entry_low"]
    entry_high = scenario["entry_high"]
    if not _is_in_entry_zone(price, entry_low, entry_high):
        return None

    mark_scenario_alerted()
    bias = scenario["bias"]
    side = "لانگ 🟢" if bias == "long" else "شورت 🔴"
    sl = scenario["stop_loss"]
    tp = scenario["take_profit"]

    return (
        f"🎯 <b>قیمت وارد ناحیه ورود شد</b>\n\n"
        f"• جهت: {side}\n"
        f"• قیمت الان: \u200e${price:,.1f}\n"
        f"• ناحیه ورود: \u200e${entry_low:,.0f} – ${entry_high:,.0f}\n"
        f"• حد ضرر: \u200e${sl:,.0f}\n"
        f"• هدف سود: \u200e${tp:,.0f}\n\n"
        f"⚠️ این هشدار اجرایی نیست — مدیریت ریسک با خودتان است."
    )
