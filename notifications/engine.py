"""Run all BTC notification checks (levels 1–3)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from config import (
    FUNDING_EXTREME,
    FNG_EXTREME_FEAR,
    FNG_EXTREME_GREED,
    LEVEL_BREAK_TIMEFRAMES,
    RSI_ALERT_TIMEFRAMES,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SMC_TIMEFRAMES,
    VOLUME_SPIKE_RATIO,
)
from market.data import fetch_ohlcv
from market.derivatives import fetch_derivatives
from market.events import get_event_risk
from market.rsi_signals import detect_rsi_divergence, detect_rsi_extreme
from market.smc import (
    compute_retest_zone,
    detect_level_break,
    detect_liquidity_grab,
    detect_mss,
    price_in_retest_zone,
)
from notifications import messages as msg
from notifications.state import already_sent, load_state, mark_sent, save_state

logger = logging.getLogger(__name__)


def _candle_time(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    closed = df.iloc[:-1] if len(df) > 1 else df
    vol = closed["Volume"]
    avg = float(vol.tail(period).mean())
    if avg == 0:
        return 1.0
    return float(vol.iloc[-1]) / avg


def run_btc_notifications() -> list[str]:
    """Scan BTC and return new Telegram HTML alerts."""
    state = load_state()
    alerts: list[str] = []

    # ── Level 1: RSI + level break ──
    for tf in RSI_ALERT_TIMEFRAMES:
        try:
            df = fetch_ohlcv(tf)
            extreme = detect_rsi_extreme(df, RSI_OVERBOUGHT, RSI_OVERSOLD)
            if extreme:
                key = f"rsi_zone_{tf}"
                fp = f"{extreme.zone.value}_{extreme.candle_ts}_{extreme.rsi_value}"
                if not already_sent(state, key, fp):
                    alerts.append(
                        msg.rsi_extreme(
                            tf,
                            extreme.zone.value,
                            extreme.rsi_value,
                            extreme.price,
                            _candle_time(extreme.candle_ts),
                        )
                    )
                    mark_sent(state, key, fp)

            div = detect_rsi_divergence(df)
            if div:
                key = f"rsi_div_{tf}"
                if not already_sent(state, key, div.fingerprint):
                    alerts.append(
                        msg.rsi_divergence(
                            tf, div.kind.value, div.rsi_value, div.price, div.note
                        )
                    )
                    mark_sent(state, key, div.fingerprint)
        except Exception:
            logger.exception("RSI check failed %s", tf)

    for tf in LEVEL_BREAK_TIMEFRAMES:
        try:
            df = fetch_ohlcv(tf)
            brk = detect_level_break(df, tf)
            if brk:
                key = f"level_break_{tf}"
                if not already_sent(state, key, brk.fingerprint):
                    alerts.append(msg.level_break(tf, brk.direction, brk.level, brk.close))
                    mark_sent(state, key, brk.fingerprint)
                    zone = compute_retest_zone(df, tf)
                    if zone:
                        mark_sent(
                            state,
                            f"retest_zone_{tf}",
                            zone.fingerprint,
                            {"zone": zone.__dict__},
                        )
        except Exception:
            logger.exception("Level break failed %s", tf)

    # ── Level 2: SMC ──
    for tf in SMC_TIMEFRAMES:
        try:
            df = fetch_ohlcv(tf)
            grab = detect_liquidity_grab(df, tf)
            if grab:
                key = f"grab_{tf}"
                if not already_sent(state, key, grab.fingerprint):
                    alerts.append(
                        msg.liquidity_grab(tf, grab.kind.value, grab.note, grab.close)
                    )
                    mark_sent(state, key, grab.fingerprint)

            mss_sig = detect_mss(df, tf)
            if mss_sig:
                key = f"mss_{tf}"
                if not already_sent(state, key, mss_sig.fingerprint):
                    alerts.append(
                        msg.mss(
                            tf,
                            mss_sig.kind.value,
                            mss_sig.note,
                            mss_sig.close,
                            mss_sig.break_level,
                        )
                    )
                    mark_sent(state, key, mss_sig.fingerprint)
        except Exception:
            logger.exception("SMC check failed %s", tf)

    # Retest zone price hit (real-time price from 1h last close)
    try:
        price_df = fetch_ohlcv("1h", candles=2)
        price = float(price_df["Close"].iloc[-1])
        for tf in LEVEL_BREAK_TIMEFRAMES:
            zkey = f"retest_zone_{tf}"
            zdata = state.get(zkey, {})
            zone_dict = zdata.get("zone")
            if not zone_dict:
                continue
            from market.smc import RetestZone

            zone = RetestZone(**{k: zone_dict[k] for k in RetestZone.__dataclass_fields__})
            hit_key = f"retest_hit_{tf}"
            hit_fp = f"hit_{zone.fingerprint}_{int(price)}"
            if price_in_retest_zone(zone, price) and not already_sent(state, hit_key, hit_fp):
                alerts.append(
                    msg.retest_hit(
                        zone.direction,
                        tf,
                        zone.entry_low,
                        zone.entry_high,
                        price,
                        zone.stop_loss,
                    )
                )
                mark_sent(state, hit_key, hit_fp)
    except Exception:
        logger.exception("Retest zone check failed")

    # ── Level 3: risk filters ──
    try:
        event_risk, event_note = get_event_risk()
        if event_risk and event_note:
            key = "macro_event"
            fp = event_note[:80]
            if not already_sent(state, key, fp):
                alerts.append(msg.macro_event(event_note))
                mark_sent(state, key, fp)
    except Exception:
        logger.exception("Event check failed")

    try:
        d = fetch_derivatives()
        if d.fear_greed_value is not None:
            if d.fear_greed_value <= FNG_EXTREME_FEAR or d.fear_greed_value >= FNG_EXTREME_GREED:
                key = "fng"
                fp = str(d.fear_greed_value)
                if not already_sent(state, key, fp):
                    alerts.append(msg.fear_greed(d.fear_greed_value, d.fear_greed_label or ""))
                    mark_sent(state, key, fp)

        if d.funding_rate is not None and abs(d.funding_rate) >= FUNDING_EXTREME:
            key = "funding"
            fp = f"{d.funding_rate:.6f}"
            if not already_sent(state, key, fp):
                alerts.append(msg.funding(d.funding_rate))
                mark_sent(state, key, fp)
    except Exception:
        logger.exception("Derivatives check failed")

    for tf in ("1h", "4h"):
        try:
            df = fetch_ohlcv(tf)
            ratio = _volume_ratio(df)
            if ratio >= VOLUME_SPIKE_RATIO:
                closed = df.iloc[:-1]
                ts = int(closed.index[-1].timestamp())
                key = f"volume_{tf}"
                fp = f"{ts}_{ratio:.1f}"
                if not already_sent(state, key, fp):
                    alerts.append(
                        msg.volume_spike(tf, ratio, float(closed["Close"].iloc[-1]))
                    )
                    mark_sent(state, key, fp)
        except Exception:
            logger.exception("Volume check failed %s", tf)

    save_state(state)
    return alerts
