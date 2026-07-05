"""Comprehensive 4-hour BTC briefing report."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import DATA_DIR
from market.context import fetch_market_context
from market.data import fetch_ohlcv
from market.events import get_event_risk
from market.indicators import bollinger_bands, ema, macd
from market.levels import find_key_levels, nearest_support_resistance
from market.news import NewsItem, fetch_btc_news
from market.smc import detect_liquidity_grab, detect_mss

logger = logging.getLogger(__name__)

BRIEFING_STATE_PATH = DATA_DIR / "briefing_state.json"


@dataclass
class TASection:
    label: str
    analysis: str
    support_zone: tuple[float, float]
    resistance_zone: tuple[float, float]
    indicators: list[tuple[str, str]]


@dataclass
class ICTScenario:
    name: str
    probability: int
    description: str
    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float | None
    triggers: list[str]


@dataclass
class BriefingReport:
    generated_at: str
    headline: str
    short_trend: str
    long_trend: str
    summary: str
    price: float
    news: list[NewsItem]
    long_term: TASection
    short_term: TASection
    long_tips: str
    short_tips: str
    bsl: list[float]
    ssl: list[float]
    scenarios: list[ICTScenario]
    long_prob: int
    short_prob: int
    final_note: str
    pending_orders: list[tuple[str, float]]
    momentum_note: str | None = None


def _closed(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1] if len(df) > 1 else df


def _trend_label(df: pd.DataFrame) -> str:
    close = df["Close"]
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    c, e20v, e50v = float(close.iloc[-1]), float(e20.iloc[-1]), float(e50.iloc[-1])
    if c > e20v > e50v:
        return "صعودی 📈"
    if c < e20v < e50v:
        return "نزولی 📉"
    return "تثبیت/رنج ↔"


def _zone(levels: list[float], price: float, side: str) -> tuple[float, float]:
    if side == "support":
        below = [x for x in levels if x <= price * 1.005]
        if len(below) >= 2:
            return round(min(below[-2:]), 0), round(max(below[-2:]), 0)
        if below:
            v = below[-1]
            return round(v * 0.998, 0), round(v, 0)
    else:
        above = [x for x in levels if x >= price * 0.995]
        if len(above) >= 2:
            return round(min(above[:2]), 0), round(max(above[:2]), 0)
        if above:
            v = above[0]
            return round(v, 0), round(v * 1.002, 0)
    return round(price * 0.97, 0), round(price * 0.98, 0)


def _res_zone(resistances: list[float], price: float) -> tuple[float, float]:
    above = [r for r in resistances if r >= price * 0.995]
    if len(above) >= 2:
        return round(above[0], 0), round(above[1], 0)
    if above:
        v = above[0]
        return round(v, 0), round(v * 1.005, 0)
    return round(price * 1.02, 0), round(price * 1.03, 0)


def _vol_ratio(df: pd.DataFrame, short: int = 5, long: int = 20) -> float:
    vol = df["Volume"]
    s = float(vol.tail(short).mean())
    l = float(vol.tail(long).mean())
    return s / l if l else 1.0


def _bb_width(close: pd.Series, period: int = 20) -> float:
    mid, upper, lower = bollinger_bands(close, period)
    m = float(mid.iloc[-1])
    if m == 0:
        return 0
    return (float(upper.iloc[-1]) - float(lower.iloc[-1])) / m * 100


def _liquidity_pools(df: pd.DataFrame, price: float) -> tuple[list[float], list[float]]:
    supports, resistances = find_key_levels(df)
    bsl = sorted([r for r in resistances if r > price * 1.001])[:2]
    ssl = sorted([s for s in supports if s < price * 0.999], reverse=True)[:2]
    if not bsl and resistances:
        bsl = [max(resistances)]
    if not ssl and supports:
        ssl = [min(supports)]
    return bsl, ssl


def _long_term_section(df: pd.DataFrame, price: float) -> TASection:
    close = df["Close"]
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    e200 = ema(close, 50) if len(close) < 200 else ema(close, min(200, len(close) - 1))
    _, _, mhist = macd(close)
    mh = float(mhist.iloc[-1])
    vol_r = _vol_ratio(df, 5, 20)
    bb_w = _bb_width(close)
    bb_w_prev = _bb_width(close.iloc[:-5]) if len(close) > 25 else bb_w

    supports, resistances = find_key_levels(df)
    sup_z = _zone(supports, price, "support")
    res_z = _res_zone(resistances, price)

    bearish_ma = float(close.iloc[-1]) < float(e50.iloc[-1])
    if vol_r < 0.75 and bearish_ma:
        analysis = (
            "بازار پس از روند نزولی در فاز تثبیت ضعیف است. "
            "حجم منقبض شده و مقاومت میانگین‌ها همچنان فشار نزولی نشان می‌دهد."
        )
    elif vol_r < 0.75:
        analysis = "فاز تثبیت با حجم پایین — بازار فاقد قاطعیت برای برگشت روند."
    elif bearish_ma:
        analysis = "فشار نزولی بلندمدت غالب است اما حجم هنوز نشانه برگشت قوی نمی‌دهد."
    else:
        analysis = "ساختار بلندمدت نسبتاً پایدار — اصلاحات در محدوده حمایت قابل مدیریت است."

    indicators: list[tuple[str, str]] = []
    indicators.append(
        (
            "Moving Average (1D)",
            "چیدمان نزولی — قیمت زیر EMA50" if bearish_ma else "قیمت بالای EMA50 — فشار صعودی",
        )
    )
    if vol_r < 0.8:
        indicators.append(("Volume (1D)", "حجم منقبض — مشارکت پایین، برگشت روند تأیید نشده"))
    else:
        indicators.append(("Volume (1D)", f"حجم {vol_r:.1f}x میانگین — مشارکت نسبتاً سالم"))
    indicators.append(
        (
            "MACD (1D)",
            "زیر خط صفر — مومنتوم نزولی" if mh < 0 else "بالای صفر — مومنتوم صعودی",
        )
    )
    if bb_w < bb_w_prev * 0.85:
        indicators.append(("BOLL (1D)", "باندها در حال فشردگی — آماده انفجار نوسان"))
    else:
        indicators.append(("BOLL (1D)", "قیمت نزدیک میانه باند — نقطه محوری"))

    return TASection("بلندمدت (1D)", analysis, sup_z, res_z, indicators)


def _short_term_section(df_1h: pd.DataFrame, df_4h: pd.DataFrame, price: float) -> TASection:
    close_1h = df_1h["Close"]
    close_4h = df_4h["Close"]
    e20_1h = ema(close_1h, 20)
    e50_1h = ema(close_1h, 50)
    gap = abs(float(e20_1h.iloc[-1]) - float(e50_1h.iloc[-1])) / price * 100
    _, _, mhist_4h = macd(close_4h)
    mh_cur = float(mhist_4h.iloc[-1])
    mh_prev = float(mhist_4h.iloc[-3]) if len(mhist_4h) > 3 else mh_cur
    vol_r = _vol_ratio(df_1h)
    bb_w = _bb_width(close_1h)
    bb_w_prev = _bb_width(close_1h.iloc[:-8]) if len(close_1h) > 28 else bb_w

    supports, resistances = find_key_levels(df_4h)
    sup, res = nearest_support_resistance(price, supports, resistances)
    sup_z = (round(min(sup, price * 0.995), 0), round(sup, 0))
    res_z = (round(res, 0), round(max(res, price * 1.005), 0))

    if gap < 0.15:
        analysis = (
            "تثبیت در سقف محدوده — EMAهای 1H در حال همگرایی، "
            "مومنتوم در چند تایم‌فریم ضعیف می‌شود."
        )
    elif vol_r < 0.7:
        analysis = "رنج با حجم رو به کاهش — بازار مردد است و منتظر ماشه جدید است."
    else:
        analysis = "نوسان در محدوده — تا شکست واضح، معامله میانی توصیه نمی‌شود."

    indicators: list[tuple[str, str]] = []
    conv = float(e20_1h.iloc[-1])
    indicators.append(
        ("Moving Average (1H)", f"همگرایی نزدیک {conv:,.0f} — نقطه تصمیم کوتاه‌مدت")
    )
    if abs(mh_cur) < abs(mh_prev):
        indicators.append(("MACD (4H)", "هیستوگرام در حال کوچک شدن — ضعف مومنتوم صعودی"))
    else:
        indicators.append(("MACD (4H)", "مومنتوم 4H هنوز فعال"))
    if vol_r < 0.8:
        indicators.append(("Volume (1H/4H)", "حجم پایین — بی‌اعتمادی برای شکست"))
    if bb_w < bb_w_prev * 0.9:
        indicators.append(("BOLL (1H)", "فشردگی باند — احتمال رنج ادامه‌دار"))

    return TASection("کوتاه‌مدت (1H/4H)", analysis, sup_z, res_z, indicators)


def _build_scenarios(
    price: float,
    bsl: list[float],
    ssl: list[float],
    df_15m: pd.DataFrame,
) -> tuple[list[ICTScenario], int, int, list[tuple[str, float]]]:
    bsl_top = bsl[-1] if bsl else price * 1.02
    bsl_mid = bsl[0] if len(bsl) > 1 else bsl_top * 0.995
    ssl_bot = ssl[-1] if ssl else price * 0.98
    ssl_mid = ssl[0] if len(ssl) > 1 else ssl_bot * 1.005

    mid = (bsl_mid + ssl_mid) / 2
    bear_bias = price > mid

    prob_short = 55 if bear_bias else 45
    prob_long = 100 - prob_short

    grab = detect_liquidity_grab(df_15m, "15m")
    mss = detect_mss(df_15m, "15m")
    triggers_bear = ["Liquidity Sweep بالای BSL", "MSS/CHoCH نزولی 5m/15m"]
    if mss and mss.kind.value == "bearish":
        triggers_bear.append("MSS نزولی فعال")
    if grab and grab.kind.value == "bearish":
        triggers_bear.append("Grab نزولی")

    triggers_bull = ["پولبک به SSL", "Bullish OB / FVG"]
    if mss and mss.kind.value == "bullish":
        triggers_bull.append("MSS صعودی فعال")
    if grab and grab.kind.value == "bullish":
        triggers_bull.append("Grab صعودی")

    sc1 = ICTScenario(
        name="سناریوی اول — Sweep بالا → شورت",
        probability=prob_short if bear_bias else prob_short - 5,
        description=(
            f"قیمت ابتدا تا {bsl_top:,.0f} حرکت و نقدینگی BSL جمع شود. "
            "پس از تأیید MSS نزولی، شورت جذاب است."
        ),
        entry_low=round(bsl_top * 0.998, 0),
        entry_high=round(bsl_top * 1.003, 0),
        stop_loss=round(bsl_top * 1.008, 0),
        tp1=round(price * 0.995, 0),
        tp2=round(ssl_mid, 0),
        triggers=triggers_bear,
    )

    sc2 = ICTScenario(
        name="سناریوی دوم — پولبک پایین → لانگ",
        probability=prob_long if not bear_bias else prob_long - 5,
        description=(
            f"اصلاح به {ssl_mid:,.0f} و ورود از Bullish OB/FVG. "
            "هدف بازگشت به BSL."
        ),
        entry_low=round(ssl_mid * 0.998, 0),
        entry_high=round(ssl_mid * 1.002, 0),
        stop_loss=round(ssl_bot * 0.995, 0),
        tp1=round(bsl_mid, 0),
        tp2=None,
        triggers=triggers_bull,
    )

    # Normalize probabilities
    total = sc1.probability + sc2.probability
    sc1.probability = round(sc1.probability / total * 100)
    sc2.probability = 100 - sc1.probability

    orders = [
        ("Buy Limit", round(ssl_mid * 1.001, 0)),
        ("Sell Limit", round(bsl_top * 0.999, 0)),
    ]
    return [sc1, sc2], sc2.probability, sc1.probability, orders


def _headline(price: float, short_t: str, long_t: str, res: float) -> str:
    if "رنج" in short_t or "تثبیت" in short_t:
        return f"BTC نزدیک {price:,.0f} در تثبیت — شکست {res:,.0f} را رصد کن"
    if "صعودی" in short_t:
        return f"BTC بالای {price:,.0f} — مقاومت {res:,.0f} محوری است"
    return f"BTC تحت فشار نزولی — حمایت {price * 0.98:,.0f} کلیدی"


def _summary(price: float, short_t: str, long_t: str, res: float) -> str:
    return (
        f"BTC در فاز {'تثبیت کوتاه‌مدت' if 'رنج' in short_t or 'تثبیت' in short_t else 'حرکت جهت‌دار'} "
        f"حدود {price:,.0f} است؛ بلندمدت {'نزولی' if 'نزولی' in long_t else 'مختلط'}. "
        f"شکست معتبر بالای {res:,.0f} با حجم، برای تغییر سناریو لازم است."
    )


def _momentum_vs_previous(metrics: dict) -> tuple[str | None, dict]:
    """Compare to last briefing snapshot."""
    prev: dict = {}
    if BRIEFING_STATE_PATH.exists():
        try:
            prev = json.loads(BRIEFING_STATE_PATH.read_text(encoding="utf-8")).get("last_metrics", {})
        except (json.JSONDecodeError, OSError):
            prev = {}

    note = None
    if prev:
        weaker = 0
        if metrics.get("macd_4h_hist", 0) < prev.get("macd_4h_hist", 0) - 5:
            weaker += 1
        if metrics.get("vol_ratio_1h", 1) < prev.get("vol_ratio_1h", 1) * 0.85:
            weaker += 1
        if metrics.get("bb_squeeze", 0) < prev.get("bb_squeeze", 999):
            weaker += 1
        if weaker >= 2:
            note = (
                "⚠️ <b>تغییر مومنتوم:</b> نسبت به گزارش قبلی ضعیف‌تر — "
                "MACD 4H، حجم و فشردگی Bollinger سیگنال احتیاط می‌دهند."
            )

    return note, metrics


def _save_briefing_state(candle_key: str, metrics: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"last_candle": candle_key, "last_metrics": metrics, "sent_at": datetime.now(timezone.utc).isoformat()}
    BRIEFING_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def current_4h_candle_key() -> str:
    now = datetime.now(timezone.utc)
    hour_block = (now.hour // 4) * 4
    return f"{now.strftime('%Y-%m-%d')}_{hour_block:02d}"


def briefing_already_sent() -> bool:
    if not BRIEFING_STATE_PATH.exists():
        return False
    try:
        state = json.loads(BRIEFING_STATE_PATH.read_text(encoding="utf-8"))
        return state.get("last_candle") == current_4h_candle_key()
    except (json.JSONDecodeError, OSError):
        return False


def build_briefing_report(*, persist: bool = True) -> BriefingReport:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    df_1d = _closed(fetch_ohlcv("1d"))
    df_4h = _closed(fetch_ohlcv("4h"))
    df_1h = _closed(fetch_ohlcv("1h"))
    df_15m = _closed(fetch_ohlcv("15m"))

    price = float(df_1h["Close"].iloc[-1])
    short_t = _trend_label(df_1h)
    long_t = _trend_label(df_1d)

    long_term = _long_term_section(df_1d, price)
    short_term = _short_term_section(df_1h, df_4h, price)

    bsl, ssl = _liquidity_pools(df_4h, price)
    scenarios, long_prob, short_prob, orders = _build_scenarios(price, bsl, ssl, df_15m)

    res_z = long_term.resistance_zone
    headline = _headline(price, short_t, long_t, res_z[1])
    summary = _summary(price, short_t, long_t, res_z[1])

    news = fetch_btc_news(4)
    risky, macro_note = get_event_risk(hours_ahead=4)
    if risky and macro_note:
        news.insert(
            0,
            NewsItem(
                category="رویداد ماکرو",
                title=macro_note,
                summary="نوسان لحظه‌ای محتمل — مدیریت ریسک ضروری.",
            ),
        )

    ctx = fetch_market_context()
    funding = next((m for m in ctx.metrics if "Funding" in m.title), None)
    fng = next((m for m in ctx.metrics if "Fear" in m.title), None)

    long_tips = (
        f"حمایت بحرانی {long_term.support_zone[0]:,.0f}–{long_term.support_zone[1]:,.0f}. "
        "شکست پایدار زیر آن با حجم، سناریوی برگشت را باطل می‌کند. "
        f"در مقاومت {long_term.resistance_zone[1]:,.0f} بدون مومنتوم صعودی، افزایش exposure توصیه نمی‌شود."
    )

    short_tips = (
        f"مقاومت {short_term.resistance_zone[0]:,.0f}–{short_term.resistance_zone[1]:,.0f} را رصد کن. "
        "شکست با حجم = لانگ سبک با SL زیر حمایت. "
        f"شکست ناموفق + برگشت زیر {short_term.support_zone[1]:,.0f} = صبر یا کاهش exposure."
    )
    if funding and "🔴" in funding.status:
        short_tips += " فاندینگ مثبت افراطی — خرید تهاجمی پرریسک."
    if fng and "🔴" in fng.status:
        short_tips += " طمع شدید — تعقیب قیمت توصیه نمی‌شود."

    bsl_top = bsl[-1] if bsl else price * 1.02
    final_note = (
        f"تا شکست معتبر بالای {bsl_top:,.0f} با حجم، خرید روی سقف توصیه نمی‌شود. "
        "Liquidity Sweep + MSS نزولی می‌تواند بهترین فرصت شورت کوتاه‌مدت باشد."
    )

    close_4h = df_4h["Close"]
    _, _, mhist = macd(close_4h)
    metrics = {
        "macd_4h_hist": float(mhist.iloc[-1]),
        "vol_ratio_1h": _vol_ratio(df_1h),
        "bb_squeeze": _bb_width(df_1h["Close"]),
        "price": price,
    }
    momentum_note, _ = _momentum_vs_previous(metrics)

    if persist:
        _save_briefing_state(current_4h_candle_key(), metrics)

    return BriefingReport(
        generated_at=now,
        headline=headline,
        short_trend=short_t,
        long_trend=long_t,
        summary=summary,
        price=price,
        news=news,
        long_term=long_term,
        short_term=short_term,
        long_tips=long_tips,
        short_tips=short_tips,
        bsl=bsl,
        ssl=ssl,
        scenarios=scenarios,
        long_prob=long_prob,
        short_prob=short_prob,
        final_note=final_note,
        pending_orders=orders,
        momentum_note=momentum_note,
    )


def run_scheduled_briefing() -> list[str]:
    """Build briefing if not yet sent this 4H candle."""
    if briefing_already_sent():
        logger.info("Briefing already sent for candle %s", current_4h_candle_key())
        return []
    from bot.briefing_format import format_briefing_report

    report = build_briefing_report(persist=True)
    return format_briefing_report(report)
