"""Institutional-style analysis: headlines, SMC scenarios, technical blocks."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from market.analysis import MarketReport
from market.indicators import atr, bollinger_bands, ema, kdj, macd_histogram, rsi
from market.news import NewsItem, fetch_market_news
from market.types import Trend


@dataclass
class IndicatorSignal:
    label: str  # e.g. "MACD"
    sentiment: str  # bullish | bearish | neutral
    timeframe: str
    note: str


@dataclass
class TechnicalBlock:
    title: str
    analysis: str
    support_zone: str
    resistance_zone: str
    breakout_level: str | None
    signals: list[IndicatorSignal] = field(default_factory=list)


@dataclass
class SMCScenario:
    name: str
    probability: int
    bias: str
    condition: str
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profits: list[float]
    note: str
    high_risk: bool = False


@dataclass
class InstitutionalBrief:
    headline: str
    short_term_label: str
    long_term_label: str
    executive_summary: str
    news_items: list[NewsItem]
    long_term: TechnicalBlock
    short_term: TechnicalBlock
    long_strategy: str
    short_strategy: str
    smc_scenarios: list[SMCScenario]
    preferred_side: str
    long_probability: int
    short_probability: int
    decision_text: str


def _round_price(p: float) -> float:
    return round(p, 0) if p >= 1000 else round(p, 1)


def _zone(low: float, high: float) -> str:
    lo, hi = _round_price(min(low, high)), _round_price(max(low, high))
    return f"${lo:,.0f}–${hi:,.0f}"


def _trend_label_fa(trend: Trend, ranging: bool) -> str:
    if ranging:
        return "تثبیت/رنج"
    return {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[trend.value]


def _macd_signal(hist_val: float, rising: bool, tf: str) -> IndicatorSignal:
    if hist_val > 0 and rising:
        return IndicatorSignal("MACD", "bullish", tf, "کراس صعودی / مومنتوم مثبت")
    if hist_val < 0 and not rising:
        return IndicatorSignal("MACD", "bearish", tf, "مومنتوم منفی پایدار")
    if hist_val > 0:
        return IndicatorSignal("MACD", "bullish", tf, "بالای صفر — مومنتوم مثبت")
    return IndicatorSignal("MACD", "bearish", tf, "زیر صفر — فشار فروش")


def _ma_signal(price: float, e20: float, e50: float, tf: str) -> IndicatorSignal:
    if price > e20 > e50:
        return IndicatorSignal("میانگین متحرک", "bullish", tf, "چینش صعودی — قیمت بالای EMA20/50")
    if price < e20 < e50:
        return IndicatorSignal("میانگین متحرک", "bearish", tf, "چینش نزولی — قیمت زیر EMA20/50")
    return IndicatorSignal("میانگین متحرک", "neutral", tf, "میانگین‌ها نامشخص یا در حال تثبیت")


def _rsi_signal(val: float, tf: str) -> IndicatorSignal:
    if val >= 70:
        return IndicatorSignal("RSI", "bearish", tf, f"RSI={val:.0f} — نزدیک اشباع خرید")
    if val <= 30:
        return IndicatorSignal("RSI", "bullish", tf, f"RSI={val:.0f} — نزدیک اشباع فروش")
    if val >= 55:
        return IndicatorSignal("RSI", "bullish", tf, f"RSI={val:.0f} — مومنتوم مثبت")
    if val <= 45:
        return IndicatorSignal("RSI", "bearish", tf, f"RSI={val:.0f} — مومنتوم ضعیف")
    return IndicatorSignal("RSI", "neutral", tf, f"RSI={val:.0f} — خنثی")


def _kdj_signal(k: float, d: float, j: float, tf: str) -> IndicatorSignal:
    if k > d and k < 80:
        return IndicatorSignal("KDJ", "bullish", tf, "کراس صعودی KDJ")
    if k < d and k > 20:
        return IndicatorSignal("KDJ", "bearish", tf, "کراس نزولی KDJ")
    if k >= 80 or j >= 90:
        return IndicatorSignal("KDJ", "bearish", tf, "اشباع خرید — احتمال اصلاح کوتاه‌مدت")
    if k <= 20:
        return IndicatorSignal("KDJ", "bullish", tf, "اشباع فروش — پتانسیل برگشت فنی")
    return IndicatorSignal("KDJ", "neutral", tf, "KDJ خنثی")


def _volume_signal(ratio: float, tf: str) -> IndicatorSignal:
    if ratio >= 1.2:
        return IndicatorSignal("حجم", "bullish", tf, f"حجم {ratio:.1f}x میانگین — مشارکت سالم")
    if ratio < 0.8:
        return IndicatorSignal("حجم", "bearish", tf, f"حجم {ratio:.1f}x — مشارکت ضعیف")
    return IndicatorSignal("حجم", "neutral", tf, f"حجم {ratio:.1f}x — متوسط")


def _bb_levels(df: pd.DataFrame) -> tuple[float, float, float]:
    mid, upper, lower = bollinger_bands(df["Close"])
    return float(mid.iloc[-1]), float(upper.iloc[-1]), float(lower.iloc[-1])


def _build_long_term_block(report: MarketReport, daily_df: pd.DataFrame) -> TechnicalBlock:
    d = report.daily
    close = daily_df["Close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    hist = macd_histogram(close)
    k_s, d_s, j_s = kdj(daily_df)

    supports = d.supports or [d.support]
    resistances = d.resistances or [d.resistance]
    sup_lo = min(supports[-2:]) if len(supports) >= 2 else d.support * 0.998
    sup_hi = max(supports[-2:]) if len(supports) >= 2 else d.support * 1.002
    res_lo = min(resistances[-2:]) if len(resistances) >= 2 else d.resistance * 0.998
    res_hi = max(resistances[-2:]) if len(resistances) >= 2 else d.resistance * 1.002
    breakout = float(ema50.iloc[-1])

    if d.is_ranging or d.trend == Trend.NEUTRAL:
        analysis = (
            "BTC در فاز تثبیت پس از نوسانات اخیر است. اندیکاتورهای کوتاه‌مدت نشانه‌های برگشت فنی "
            "دارند، اما میانگین‌های بلندمدت هنوز مقاومت جدی ایجاد می‌کنند. "
            "تثبیت بالای مقاومت کلیدی برای تأیید برگشت روند لازم است."
        )
    elif d.trend == Trend.BEARISH:
        analysis = (
            "روند بلندمدت همچنان تحت فشار است و قیمت زیر سطوح کلیدی میانگین حرکت می‌کند. "
            "هر بازگشت صعودی تا زمانی که مقاومت اصلی نشکند، بیشتر اصلاح محسوب می‌شود."
        )
    else:
        analysis = (
            "روند بلندمدت صعودی است، اما نزدیک مقاومت‌های مهم ممکن است نوسان افزایش یابد. "
            "حفظ سطح حمایت برای ادامه مسیر صعودی ضروری است."
        )

    signals = [
        _macd_signal(float(hist.iloc[-1]), float(hist.iloc[-1]) > float(hist.iloc[-2]), "1D"),
        _ma_signal(d.price, float(ema20.iloc[-1]), float(ema50.iloc[-1]), "1D"),
        _rsi_signal(d.rsi, "1D"),
        _kdj_signal(float(k_s.iloc[-1]), float(d_s.iloc[-1]), float(j_s.iloc[-1]), "1D"),
        _volume_signal(d.volume_ratio, "1D"),
    ]

    return TechnicalBlock(
        title="بلندمدت (روزانه)",
        analysis=analysis,
        support_zone=_zone(sup_lo, sup_hi),
        resistance_zone=_zone(res_lo, res_hi),
        breakout_level=f"${_round_price(breakout):,.0f} (EMA50)",
        signals=signals,
    )


def _build_short_term_block(
    report: MarketReport, h4_df: pd.DataFrame, h1_df: pd.DataFrame
) -> TechnicalBlock:
    h4, h1 = report.h4, report.h1
    _, h4_upper, _ = _bb_levels(h4_df)
    h1_mid, h1_upper, _ = _bb_levels(h1_df)

    res_lo = min(h4.resistance, h1_upper) * 0.998
    res_hi = max(h4.resistance, h4_upper, h1_upper)
    sup = h1_mid

    if h1.trend == Trend.BULLISH and h4.trend in (Trend.BULLISH, Trend.NEUTRAL):
        analysis = (
            f"BTC در روند صعودی کوتاه‌مدت است و نزدیک مقاومت {_round_price(res_hi):,.0f} تست می‌شود. "
            f"شکست و تثبیت بالای این محدوده می‌تواند مسیر را ادامه دهد؛ "
            f"از دست رفتن حمایت {_round_price(sup):,.0f} سناریوی اصلاح را فعال می‌کند."
        )
    elif h1.trend == Trend.BEARISH:
        analysis = (
            f"فشار فروش کوتاه‌مدت غالب است. مقاومت {_zone(res_lo, res_hi)} و "
            f"حمایت کلیدی {_round_price(sup):,.0f} سطوح تصمیم‌گیری هستند."
        )
    else:
        analysis = (
            "بازار کوتاه‌مدت مختلط است — روند ۱H و ۴H کاملاً هم‌جهت نیستند. "
            "صبر برای تأیید شکست یکی از محدوده‌های کلیدی منطقی‌تر است."
        )

    hist4 = macd_histogram(h4_df["Close"])
    hist1 = macd_histogram(h1_df["Close"])
    k4, d4, j4 = kdj(h4_df)
    k1, d1, j1 = kdj(h1_df)

    signals = [
        _ma_signal(h1.price, h1.ema20, h1.ema50, "1H/4H"),
        _macd_signal(float(hist1.iloc[-1]), float(hist1.iloc[-1]) > float(hist1.iloc[-2]), "1H/4H"),
        _rsi_signal(h1.rsi, "1H/4H"),
        _kdj_signal(float(k4.iloc[-1]), float(d4.iloc[-1]), float(j4.iloc[-1]), "1H/4H"),
        _volume_signal(h1.volume_ratio, "1H"),
    ]

    return TechnicalBlock(
        title="کوتاه‌مدت (۴H + ۱H)",
        analysis=analysis,
        support_zone=f"${_round_price(sup):,.0f} (میان‌بند بولینگر ۱H)",
        resistance_zone=_zone(res_lo, res_hi),
        breakout_level=f"${_round_price(res_hi):,.0f}",
        signals=signals,
    )


def _build_smc_scenarios(
    report: MarketReport,
    h4_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    long_prob: int,
) -> list[SMCScenario]:
    h4, h1 = report.h4, report.h1
    h4_atr = float(atr(h4_df).iloc[-1])
    _, h4_upper, _ = _bb_levels(h4_df)
    _, h1_upper, _ = _bb_levels(h1_df)

    breakout = _round_price(max(h4.resistance, h4_upper, h1_upper))
    support = _round_price(h1.ema20 if h1.ema20 < h1.price else report.h1.support)

    entry_low = _round_price(breakout * 0.996)
    entry_high = _round_price(breakout * 0.999)
    sl_long = _round_price(breakout * 0.992)
    tp1 = _round_price(breakout + h4_atr * 1.0)
    tp2 = _round_price(breakout + h4_atr * 2.0)
    tp3 = _round_price(breakout + h4_atr * 3.0)

    long_scenario = SMCScenario(
        name="سناریوی ۱ — Breakout + Retest (لانگ)",
        probability=long_prob,
        bias="long",
        condition=(
            f"اگر قیمت بالای ${_round_price(breakout):,.0f} یک کندل ۱H ببندد "
            f"و سپس به {_zone(entry_low, entry_high)} پولبک بزند"
        ),
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=sl_long,
        take_profits=[tp1, tp2, tp3],
        note="امن‌ترین ورود لانگ — منتظر شکست و پولبک باشید، نه خرید قبل از مقاومت.",
        high_risk=report.daily.trend == Trend.BEARISH,
    )

    sweep_hi = _round_price(breakout * 1.003)
    sweep_top = _round_price(breakout * 1.006)
    short_entry_lo = _round_price(breakout * 0.999)
    short_entry_hi = sweep_hi
    short_sl = _round_price(sweep_top * 1.003)
    stp1 = _round_price(support)
    stp2 = _round_price(support - h4_atr * 1.5)

    short_scenario = SMCScenario(
        name="سناریوی ۲ — Liquidity Sweep (شورت)",
        probability=100 - long_prob,
        bias="short",
        condition=(
            f"اگر قیمت تا {_zone(sweep_hi, sweep_top)} بالا برود، نقدینگی سقف جمع شود "
            f"و سپس در ۱H ساختار نزولی (MSS) بدهد"
        ),
        entry_low=short_entry_lo,
        entry_high=short_entry_hi,
        stop_loss=short_sl,
        take_profits=[stp1, stp2],
        note="فقط با تأیید نزولی — اگر روزانه صعودی است، شورت پرریسک است.",
        high_risk=report.daily.trend == Trend.BULLISH,
    )

    return [long_scenario, short_scenario]


def _probabilities(report: MarketReport, prev: dict | None) -> tuple[int, int, str, str]:
    long_score = 50
    if report.daily.trend == Trend.BULLISH:
        long_score += 15
    elif report.daily.trend == Trend.BEARISH:
        long_score -= 15

    if report.h4.trend == Trend.BULLISH:
        long_score += 10
    elif report.h4.trend == Trend.BEARISH:
        long_score -= 10

    if report.h1.trend == Trend.BULLISH:
        long_score += 10
    elif report.h1.trend == Trend.BEARISH:
        long_score -= 10

    long_score += int((report.checklist.score - 50) * 0.2)
    long_score += int((report.quality_score - 50) * 0.15)

    if prev and prev.get("checklist_score"):
        if report.checklist.score > prev["checklist_score"]:
            long_score += 5
        elif report.checklist.score < prev["checklist_score"]:
            long_score -= 5
        if report.h4.volume_ratio if hasattr(report.h4, "volume_ratio") else 0:
            if report.h4.volume_ratio >= 1.0 and prev.get("price"):
                long_score += 3

    long_prob = max(25, min(80, long_score))
    short_prob = 100 - long_prob

    if long_prob >= short_prob + 15:
        side = "long"
        decision = (
            f"لانگ قوی‌تر از شورت است ({long_prob}% vs {short_prob}%). "
            f"قبل از شکست مقاومت وارد خرید نشوید — احتمال فیک‌اوت وجود دارد. "
            f"اگر مجبور به یک معامله باشید: تثبیت بالای مقاومت، سپس لانگ روی پولبک."
        )
    elif short_prob > long_prob + 10:
        side = "short"
        decision = (
            f"شورت نسبت به لانگ برتری دارد ({short_prob}% vs {long_prob}%) — "
            f"اما فقط با تأیید نزولی در ۱H وارد شوید."
        )
    else:
        side = "wait"
        decision = (
            f"بازار مختلط است (لانگ {long_prob}% / شورت {short_prob}%). "
            f"صبر برای شکست قطعی یکی از سطوح کلیدی منطقی‌تر است."
        )

    return long_prob, short_prob, side, decision


def _headline(report: MarketReport, resistance: float, support: float) -> str:
    res = _round_price(resistance)
    sup = _round_price(support)
    if report.h1.price >= resistance * 0.995:
        return f"BTC در آستانه مقاومت ${res:,.0f} با سیگنال‌های مختلط؛ حمایت ${sup:,.0f} را رصد کن"
    if report.h1.price <= support * 1.005:
        return f"BTC نزدیک حمایت ${sup:,.0f}؛ شکست مقاومت ${res:,.0f} جهت را تعیین می‌کند"
    return f"BTC بین حمایت ${sup:,.0f} و مقاومت ${res:,.0f} — منتظر شکست محدوده"


def build_institutional_brief(
    report: MarketReport,
    daily_df: pd.DataFrame,
    h4_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    previous: dict | None = None,
) -> InstitutionalBrief:
    news = fetch_market_news(report.derivatives, report.event_risk_note)
    long_term = _build_long_term_block(report, daily_df)
    short_term = _build_short_term_block(report, h4_df, h1_df)

    long_prob, short_prob, preferred, decision = _probabilities(report, previous)
    smc = _build_smc_scenarios(report, h4_df, h1_df, long_prob)

    st_label = _trend_label_fa(report.h1.trend, False)
    if report.h1.is_ranging:
        st_label += " (رنج)"
    lt_label = _trend_label_fa(report.daily.trend, False)
    if report.daily.is_ranging:
        lt_label += " (رنج)"

    res_val = max(report.h4.resistance, report.h1.resistance)
    sup_val = min(report.h4.support, report.h1.support)

    exec_parts = [
        f"BTC در کوتاه‌مدت {st_label} و در بلندمدت {lt_label} دیده می‌شود.",
        short_term.analysis,
    ]
    if report.event_risk:
        exec_parts.append("رویداد ماکرو نزدیک — احتیاط در ورود قطعی توصیه می‌شود.")

    long_strat = (
        f"بلندمدت: محتاطانه بمان. حمایت {long_term.support_zone} را رصد کن. "
        f"شکست پایدار زیر این محدوده با حجم، سناریوی صعودی را باطل می‌کند. "
        f"فقط پس از شکست و تثبیت بالای {long_term.breakout_level or long_term.resistance_zone} "
        f"انباشت جدی‌تر را بررسی کن."
    )

    short_strat = (
        f"کوتاه‌مدت: حمایت {short_term.support_zone} کلیدی است. "
        f"شکست زیر آن با حجم → کاهش/خروج از لانگ. "
        f"شکست و تثبیت بالای {short_term.resistance_zone} با حجم → فرصت لانگ هدف‌دار. "
        f"در اشباع اندیکاتور (KDJ/RSI بالا) احتیاط از تعقیب قیمت."
    )

    return InstitutionalBrief(
        headline=_headline(report, res_val, sup_val),
        short_term_label=f"کوتاه‌مدت: {st_label}",
        long_term_label=f"بلندمدت: {lt_label}",
        executive_summary=" ".join(exec_parts),
        news_items=news,
        long_term=long_term,
        short_term=short_term,
        long_strategy=long_strat,
        short_strategy=short_strat,
        smc_scenarios=smc,
        preferred_side=preferred,
        long_probability=long_prob,
        short_probability=short_prob,
        decision_text=decision,
    )
