"""RSI overbought/oversold and divergence Telegram alerts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import DATA_DIR, RSI_ALERT_TIMEFRAMES, RSI_OVERBOUGHT, RSI_OVERSOLD
from market.data import fetch_ohlcv
from market.rsi_signals import (
    DivergenceType,
    RsiZone,
    detect_rsi_divergence,
    detect_rsi_extreme,
)

logger = logging.getLogger(__name__)

STATE_PATH = DATA_DIR / "rsi_alerts_state.json"

_ZONE_FA = {
    RsiZone.OVERBOUGHT: "اوربای (اشباع خرید) 🔴",
    RsiZone.OVERSOLD: "اورسولد (اشباع فروش) 🟢",
}

_DIV_FA = {
    DivergenceType.BULLISH: "واگرایی صعودی (Bullish) 📈",
    DivergenceType.BEARISH: "واگرایی نزولی (Bearish) 📉",
}


def _ltr(text: str) -> str:
    return f"\u200e{text}"


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load RSI alert state")
        return {}


def _save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _tf_label(tf: str) -> str:
    from config import STATUS_TIMEFRAMES

    return STATUS_TIMEFRAMES.get(tf, {}).get("label", tf)


def _fmt_extreme_alert(tf: str, zone: RsiZone, rsi_value: float, price: float, candle_ts: int) -> str:
    from datetime import datetime, timezone

    candle_time = datetime.fromtimestamp(candle_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"\u200f🔔 <b>هشدار RSI — {_tf_label(tf)}</b>\n"
        f"{'─' * 18}\n"
        f"وضعیت: <b>{_ZONE_FA[zone]}</b>\n"
        f"RSI (کندل بسته): {_ltr(str(rsi_value))}\n"
        f"قیمت: {_ltr(f'${price:,.1f}')}\n"
        f"کندل: {_ltr(candle_time)}\n"
        f"{'─' * 18}\n"
        f"⚠️ ورود به ناحیه اشباع — ورود مستقیم توصیه نمی‌شود."
    )


def _fmt_divergence_alert(tf: str, div) -> str:
    return (
        f"\u200f📐 <b>واگرایی RSI — {_tf_label(tf)}</b>\n"
        f"{'─' * 18}\n"
        f"نوع: <b>{_DIV_FA[div.kind]}</b>\n"
        f"RSI الان: {_ltr(str(div.rsi_value))}\n"
        f"قیمت: {_ltr(f'${div.price:,.1f}')}\n"
        f"جزئیات: {div.note}\n"
        f"{'─' * 18}\n"
        f"💡 واگرایی = هشدار احتمال برگشت؛ منتظر تأیید قیمت باشید."
    )


def check_rsi_alerts() -> list[str]:
    """
    Scan 15m / 1h / 4h for RSI extremes and divergences.
    Returns Telegram HTML messages for new signals only.
    """
    state = _load_state()
    messages: list[str] = []

    for tf in RSI_ALERT_TIMEFRAMES:
        try:
            df = fetch_ohlcv(tf)
            closed_ts = int(df.index[-2].timestamp()) if len(df) >= 2 else 0

            extreme = detect_rsi_extreme(df, RSI_OVERBOUGHT, RSI_OVERSOLD)
            zone_key = f"{tf}_zone"
            prev_zone = state.get(zone_key, {})

            if extreme:
                already_sent = (
                    prev_zone.get("candle_ts") == extreme.candle_ts
                    and prev_zone.get("zone") == extreme.zone.value
                )
                if not already_sent:
                    messages.append(
                        _fmt_extreme_alert(
                            tf, extreme.zone, extreme.rsi_value, extreme.price, extreme.candle_ts
                        )
                    )
                    state[zone_key] = {
                        "candle_ts": extreme.candle_ts,
                        "zone": extreme.zone.value,
                        "rsi": extreme.rsi_value,
                    }
            else:
                state[zone_key] = {"candle_ts": closed_ts, "zone": None}

            divergence = detect_rsi_divergence(df)
            div_key = f"{tf}_div"
            prev_div = state.get(div_key, {})

            if divergence:
                already_sent = prev_div.get("fingerprint") == divergence.fingerprint
                if not already_sent:
                    messages.append(_fmt_divergence_alert(tf, divergence))
                    state[div_key] = {
                        "candle_ts": divergence.candle_ts,
                        "fingerprint": divergence.fingerprint,
                        "kind": divergence.kind.value,
                    }

        except Exception:
            logger.exception("RSI alert check failed for %s", tf)

    _save_state(state)
    return messages
