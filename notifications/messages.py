"""Persian Telegram HTML formatters for BTC alerts."""

from __future__ import annotations

RLM = "\u200f"
LRM = "\u200e"


def ltr(text: str) -> str:
    return f"{LRM}{text}"


def wrap(text: str) -> str:
    return f"{RLM}{text.strip()}"


def _tf_label(tf: str) -> str:
    from config import TIMEFRAME_LABELS

    return TIMEFRAME_LABELS.get(tf, tf)


def rsi_extreme(tf: str, zone: str, rsi_val: float, price: float, candle_time: str) -> str:
    zone_fa = "اوربای 🔴" if zone == "overbought" else "اورسولد 🟢"
    return wrap(
        f"🔔 <b>RSI — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"وضعیت: <b>{zone_fa}</b>\n"
        f"RSI: {ltr(str(rsi_val))}\n"
        f"قیمت: {ltr(f'${price:,.1f}')}\n"
        f"کندل: {ltr(candle_time)}\n"
        f"{'─' * 16}\n"
        f"⚠️ ورود به ناحیه اشباع — منتظر تأیید باشید."
    )


def rsi_divergence(tf: str, kind: str, rsi_val: float, price: float, note: str) -> str:
    kind_fa = "صعودی 📈" if kind == "bullish" else "نزولی 📉"
    return wrap(
        f"📐 <b>واگرایی RSI — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"نوع: <b>{kind_fa}</b>\n"
        f"RSI: {ltr(str(rsi_val))}\n"
        f"قیمت: {ltr(f'${price:,.1f}')}\n"
        f"{note}\n"
        f"{'─' * 16}\n"
        f"💡 منتظر تأیید قیمت باشید."
    )


def level_break(tf: str, direction: str, level: float, close: float) -> str:
    dir_fa = "صعودی ⬆️" if direction == "up" else "نزولی ⬇️"
    return wrap(
        f"⚡ <b>شکست سطح — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"جهت: <b>{dir_fa}</b>\n"
        f"سطح: {ltr(f'${level:,.0f}')}\n"
        f"بسته: {ltr(f'${close:,.1f}')}\n"
        f"{'─' * 16}"
    )


def liquidity_grab(tf: str, kind: str, note: str, close: float) -> str:
    kind_fa = "BSL sweep 🟢" if kind == "bullish" else "SSL sweep 🔴"
    return wrap(
        f"🎯 <b>Liquidity Grab — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"نوع: <b>{kind_fa}</b>\n"
        f"قیمت: {ltr(f'${close:,.1f}')}\n"
        f"{note}\n"
        f"{'─' * 16}"
    )


def mss(tf: str, kind: str, note: str, close: float, level: float) -> str:
    kind_fa = "صعودی 📈" if kind == "bullish" else "نزولی 📉"
    return wrap(
        f"🔄 <b>MSS — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"نوع: <b>{kind_fa}</b>\n"
        f"سطح: {ltr(f'${level:,.0f}')}\n"
        f"بسته: {ltr(f'${close:,.1f}')}\n"
        f"{note}\n"
        f"{'─' * 16}"
    )


def retest_hit(direction: str, tf: str, low: float, high: float, price: float, sl: float) -> str:
    side = "لانگ 🟢" if direction == "long" else "شورت 🔴"
    return wrap(
        f"✅ <b>Breakout + Retest — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"جهت: <b>{side}</b>\n"
        f"قیمت: {ltr(f'${price:,.1f}')}\n"
        f"ناحیه: {ltr(f'${low:,.0f}–${high:,.0f}')}\n"
        f"حد ضرر: {ltr(f'${sl:,.0f}')}\n"
        f"{'─' * 16}\n"
        f"⚠️ مدیریت ریسک با خودتان است."
    )


def macro_event(note: str) -> str:
    return wrap(
        f"⚠️ <b>رویداد ماکرو</b>\n"
        f"{'─' * 16}\n"
        f"{note}\n"
        f"{'─' * 16}\n"
        f"⛔ ورود تهاجمی توصیه نمی‌شود."
    )


def fear_greed(value: int, label: str) -> str:
    return wrap(
        f"😱 <b>ترس و طمع افراطی</b>\n"
        f"{'─' * 16}\n"
        f"شاخص: <b>{value}</b> ({label})\n"
        f"{'─' * 16}"
    )


def funding(rate: float) -> str:
    pct = rate * 100
    return wrap(
        f"📊 <b>Funding افراطی BTC</b>\n"
        f"{'─' * 16}\n"
        f"نرخ: {ltr(f'{pct:.4f}')}%\n"
        f"{'─' * 16}\n"
        f"احتمال اصلاح/اسکویز افزایش یافته."
    )


def volume_spike(tf: str, ratio: float, close: float) -> str:
    return wrap(
        f"📈 <b>حجم غیرعادی — {_tf_label(tf)}</b>\n"
        f"{'─' * 16}\n"
        f"نسبت: <b>{ratio:.1f}x</b> میانگین\n"
        f"قیمت: {ltr(f'${close:,.1f}')}\n"
        f"{'─' * 16}"
    )
