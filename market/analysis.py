"""Multi-timeframe market analysis engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

from market.checklist import ChecklistResult, run_checklist
from market.derivatives import DerivativesSnapshot, fetch_derivatives
from market.indicators import ema, macd_histogram, rsi
from market.levels import find_key_levels, nearest_support_resistance
from market.types import Bias, TimeframeAnalysis, Trend
from tracking.tuning import (
    get_min_checklist_passed,
    get_min_checklist_score,
    get_min_entry_score,
)

@dataclass
class TradeScenario:
    bias: Bias
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profit: float
    condition: str
    reason: str
    confidence: int
    counter_trend: bool = False


@dataclass
class MarketReport:
    generated_at: str
    symbol: str
    daily: TimeframeAnalysis
    h4: TimeframeAnalysis
    h1: TimeframeAnalysis
    derivatives: DerivativesSnapshot
    checklist: ChecklistResult
    allowed_bias: Bias
    scenario: TradeScenario | None
    summary_lines: list[str]
    quality_score: int
    action: str  # full | watch | wait | no_signal


def _detect_trend(close: pd.Series, ema20: pd.Series, ema50: pd.Series) -> Trend:
    c = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])
    if c > e20 > e50:
        return Trend.BULLISH
    if c < e20 < e50:
        return Trend.BEARISH
    return Trend.NEUTRAL


def _is_ranging(df: pd.DataFrame, threshold_pct: float = 2.0, candles: int = 20) -> bool:
    recent = df.tail(candles)
    high = float(recent["High"].max())
    low = float(recent["Low"].min())
    mid = (high + low) / 2
    if mid == 0:
        return True
    return ((high - low) / mid) * 100 < threshold_pct


def _volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    vol = df["Volume"]
    avg = float(vol.tail(period).mean())
    if avg == 0:
        return 1.0
    return float(vol.iloc[-1]) / avg


def _macd_rising(hist: pd.Series) -> bool:
    if len(hist) < 3:
        return False
    return float(hist.iloc[-1]) > float(hist.iloc[-2])


def _score_timeframe(
    trend: Trend,
    rsi_val: float,
    macd_val: float,
    macd_rising: bool,
    volume_ratio: float,
    is_ranging: bool,
    align_with: Trend | None = None,
) -> tuple[int, list[str]]:
    score = 50
    notes: list[str] = []

    if trend == Trend.BULLISH:
        score += 10
        notes.append("روند صعودی")
    elif trend == Trend.BEARISH:
        score += 10
        notes.append("روند نزولی")
    else:
        notes.append("روند خنثی/نامشخص")
        score -= 10

    if align_with and trend == align_with:
        score += 15
        notes.append("هم‌راستا با تایم‌فریم بالاتر")
    elif align_with and trend != Trend.NEUTRAL and trend != align_with:
        score -= 20
        notes.append("خلاف تایم‌فریم بالاتر — پرریسک")

    if 40 <= rsi_val <= 60:
        score += 10
    elif rsi_val > 70:
        score -= 12
        notes.append("RSI نزدیک اشباع خرید")
    elif rsi_val < 30:
        score -= 12
        notes.append("RSI نزدیک اشباع فروش")

    if macd_val > 0 and macd_rising:
        score += 10
    elif macd_val < 0 and not macd_rising:
        score += 8
    elif macd_val > 0:
        score += 4
    else:
        score -= 4

    if volume_ratio >= 1.2:
        score += 10
        notes.append("حجم بالاتر از میانگین")
    elif volume_ratio < 0.8:
        score -= 8
        notes.append("حجم پایین")

    if is_ranging:
        score -= 15
        notes.append("بازار در رنج")

    return max(0, min(100, score)), notes


def analyze_timeframe(
    df: pd.DataFrame,
    key: str,
    label: str,
    align_with: Trend | None = None,
) -> TimeframeAnalysis:
    close = df["Close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    hist = macd_histogram(close)
    rsi_val = float(rsi(close).iloc[-1])
    macd_val = float(hist.iloc[-1])
    macd_up = _macd_rising(hist)
    trend = _detect_trend(close, ema20, ema50)
    supports, resistances = find_key_levels(df)
    price = float(close.iloc[-1])
    support, resistance = nearest_support_resistance(price, supports, resistances)
    vol_ratio = _volume_ratio(df)
    ranging = _is_ranging(df)
    score, notes = _score_timeframe(trend, rsi_val, macd_val, macd_up, vol_ratio, ranging, align_with)

    return TimeframeAnalysis(
        key=key,
        label=label,
        price=price,
        trend=trend,
        rsi=round(rsi_val, 1),
        macd_hist=round(macd_val, 2),
        macd_rising=macd_up,
        ema20=float(ema20.iloc[-1]),
        ema50=float(ema50.iloc[-1]),
        support=support,
        resistance=resistance,
        supports=supports,
        resistances=resistances,
        volume_ratio=round(vol_ratio, 2),
        is_ranging=ranging,
        score=score,
        notes=notes,
    )


def _allowed_bias_from_daily(daily: Trend) -> Bias:
    if daily == Trend.BULLISH:
        return "long"
    if daily == Trend.BEARISH:
        return "short"
    return "wait"


def _build_scenario(
    daily: TimeframeAnalysis,
    h4: TimeframeAnalysis,
    h1: TimeframeAnalysis,
    checklist: ChecklistResult,
) -> TradeScenario | None:
    bias = _allowed_bias_from_daily(daily.trend)
    if bias == "wait":
        return None

    # Require minimum alignment before proposing any scenario
    if h4.trend != Trend.NEUTRAL and h4.trend != daily.trend:
        return None
    if h1.trend != Trend.NEUTRAL and h1.trend != daily.trend:
        return None

    if bias == "long":
        entry_low = round(min(h4.ema20, h4.support) * 0.999, 1)
        entry_high = round(h4.ema20 * 1.001, 1)
        stop_loss = round(h4.support * 0.995, 1)
        take_profit = round(h4.resistance, 1)
        condition = f"اگر قیمت به ${entry_low:,.0f} – ${entry_high:,.0f} رسید"
        reason = (
            "روند روزانه صعودی است و ۴H/۱H مخالف نیستند؛ "
            "ورود روی پولبک منطقی است. شورت خلاف بلندمدت — پرریسک."
        )
    else:
        entry_low = round(h4.ema20 * 0.999, 1)
        entry_high = round(max(h4.ema20, h4.resistance) * 1.001, 1)
        stop_loss = round(h4.resistance * 1.005, 1)
        take_profit = round(h4.support, 1)
        condition = f"اگر قیمت به ${entry_low:,.0f} – ${entry_high:,.0f} رسید (پولبک)"
        reason = (
            "روند روزانه نزولی است و ۴H/۱H مخالف نیستند؛ "
            "ورود شورت روی پولبک منطقی است. لانگ خلاف بلندمدت — پرریسک."
        )

    tf_confidence = int(np.mean([daily.score, h4.score, h1.score]))
    confidence = int(round(tf_confidence * 0.6 + checklist.score * 0.4))
    confidence = max(0, min(100, confidence))

    return TradeScenario(
        bias=bias,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=stop_loss,
        take_profit=take_profit,
        condition=condition,
        reason=reason,
        confidence=confidence,
        counter_trend=False,
    )


def _trend_fa(trend: Trend) -> str:
    return {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[trend.value]


def _determine_action(
    daily: TimeframeAnalysis,
    h4: TimeframeAnalysis,
    scenario: TradeScenario | None,
    checklist: ChecklistResult,
) -> str:
    if not scenario:
        if daily.is_ranging or h4.is_ranging:
            return "wait"
        return "no_signal"

    min_entry = get_min_entry_score()
    min_checklist = get_min_checklist_score()
    min_passed = get_min_checklist_passed()

    if (
        scenario.confidence >= min_entry
        and checklist.score >= min_checklist
        and checklist.passed >= min_passed
        and not daily.is_ranging
        and not h4.is_ranging
    ):
        return "full"

    if scenario.confidence >= 55 or checklist.score >= 55:
        return "watch"

    if daily.is_ranging or h4.is_ranging:
        return "wait"

    return "no_signal"


def build_report(
    daily_df: pd.DataFrame,
    h4_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    generated_at: str,
    derivatives: DerivativesSnapshot | None = None,
) -> MarketReport:
    if derivatives is None:
        derivatives = fetch_derivatives()

    daily = analyze_timeframe(daily_df, "1d", "روزانه")
    h4 = analyze_timeframe(h4_df, "4h", "۴ ساعته", align_with=daily.trend)
    h1 = analyze_timeframe(h1_df, "1h", "۱ ساعته", align_with=daily.trend)

    allowed = _allowed_bias_from_daily(daily.trend)
    checklist = run_checklist(daily, h4, h1, allowed, derivatives)
    scenario = _build_scenario(daily, h4, h1, checklist)
    quality = int(round(np.mean([daily.score, h4.score, h1.score]) * 0.5 + checklist.score * 0.5))
    action = _determine_action(daily, h4, scenario, checklist)

    summary: list[str] = []
    summary.append(f"قیمت الان: ${h1.price:,.1f}")

    if daily.trend == Trend.BULLISH:
        summary.append("جهت اصلی (روزانه): 📈 صعودی — فقط لانگ یا صبر")
        summary.append("⛔ شورت توصیه نمی‌شود — خلاف روند بلندمدت، پرریسک")
    elif daily.trend == Trend.BEARISH:
        summary.append("جهت اصلی (روزانه): 📉 نزولی — فقط شورت یا صبر")
        summary.append("⛔ لانگ توصیه نمی‌شود — خلاف روند بلندمدت، پرریسک")
    else:
        summary.append("جهت روزانه: خنثی — فعلاً صبر کن")

    summary.append(f"۴ ساعته: {_trend_fa(h4.trend)} | ۱ ساعته: {_trend_fa(h1.trend)}")
    summary.append(f"چک‌لیست کیفیت: {checklist.passed}/{checklist.total} ({checklist.score}%)")

    if derivatives.fear_greed_value is not None:
        summary.append(f"شاخص ترس/طمع: {derivatives.fear_greed_value} ({derivatives.fear_greed_label})")

    if action == "full":
        summary.append("✅ شرایط مناسب برای سناریو ورود")
    elif action == "watch":
        summary.append("👀 نظارت — هنوز ورود قطعی نیست")
    elif action == "wait":
        summary.append("⏸ بازار در رنج یا شرایط نامناسب — صبر")
    else:
        summary.append("⏳ فعلاً سیگنال قوی نیست — صبر کن")

    return MarketReport(
        generated_at=generated_at,
        symbol="BTC/USD",
        daily=daily,
        h4=h4,
        h1=h1,
        derivatives=derivatives,
        checklist=checklist,
        allowed_bias=allowed,
        scenario=scenario,
        summary_lines=summary,
        quality_score=quality,
        action=action,
    )
