"""Multi-timeframe market analysis engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd

from market.indicators import ema, macd_histogram, rsi


class Trend(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


Bias = Literal["long", "short", "wait"]


@dataclass
class TimeframeAnalysis:
    key: str
    label: str
    price: float
    trend: Trend
    rsi: float
    macd_hist: float
    ema20: float
    ema50: float
    support: float
    resistance: float
    volume_ratio: float
    is_ranging: bool
    score: int
    notes: list[str] = field(default_factory=list)


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
    allowed_bias: Bias
    scenario: TradeScenario | None
    summary_lines: list[str]
    quality_score: int
    action: str  # full | watch | wait | no_signal


def _swing_levels(df: pd.DataFrame, lookback: int = 30) -> tuple[float, float]:
    recent = df.tail(lookback)
    return float(recent["Low"].min()), float(recent["High"].max())


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


def _score_timeframe(
    trend: Trend,
    rsi_val: float,
    macd_val: float,
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
        score -= 10
        notes.append("RSI نزدیک اشباع خرید")
    elif rsi_val < 30:
        score -= 10
        notes.append("RSI نزدیک اشباع فروش")

    if macd_val > 0:
        score += 5
    else:
        score -= 5

    if volume_ratio >= 1.2:
        score += 10
        notes.append("حجم بالاتر از میانگین")
    elif volume_ratio < 0.8:
        score -= 5
        notes.append("حجم پایین")

    if is_ranging:
        score -= 15
        notes.append("بازار در رنج")

    return max(0, min(100, score)), notes


def analyze_timeframe(df: pd.DataFrame, key: str, label: str, align_with: Trend | None = None) -> TimeframeAnalysis:
    close = df["Close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    rsi_val = float(rsi(close).iloc[-1])
    macd_val = float(macd_histogram(close).iloc[-1])
    trend = _detect_trend(close, ema20, ema50)
    support, resistance = _swing_levels(df)
    vol_ratio = _volume_ratio(df)
    ranging = _is_ranging(df)
    score, notes = _score_timeframe(trend, rsi_val, macd_val, vol_ratio, ranging, align_with)

    return TimeframeAnalysis(
        key=key,
        label=label,
        price=float(close.iloc[-1]),
        trend=trend,
        rsi=round(rsi_val, 1),
        macd_hist=round(macd_val, 2),
        ema20=float(ema20.iloc[-1]),
        ema50=float(ema50.iloc[-1]),
        support=support,
        resistance=resistance,
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


def _build_scenario(daily: TimeframeAnalysis, h4: TimeframeAnalysis, h1: TimeframeAnalysis) -> TradeScenario | None:
    bias = _allowed_bias_from_daily(daily.trend)
    if bias == "wait":
        return None

    if bias == "long":
        entry_low = round(min(h4.ema20, h4.support) * 0.999, 1)
        entry_high = round(h4.ema20 * 1.001, 1)
        stop_loss = round(h4.support * 0.995, 1)
        take_profit = round(h4.resistance, 1)
        condition = f"اگر قیمت به ${entry_low:,.0f} – ${entry_high:,.0f} رسید"
        reason = (
            "روند روزانه صعودی است؛ ورود روی پولبک به حمایت/EMA منطقی است. "
            "شورت خلاف روند بلندمدت — پرریسک."
        )
        counter = False
    else:
        entry_low = round(h4.ema20 * 0.999, 1)
        entry_high = round(max(h4.ema20, h4.resistance) * 1.001, 1)
        stop_loss = round(h4.resistance * 1.005, 1)
        take_profit = round(h4.support, 1)
        condition = f"اگر قیمت به ${entry_low:,.0f} – ${entry_high:,.0f} رسید (پولبک)"
        reason = (
            "روند روزانه نزولی است؛ ورود شورت روی پولبک به مقاومت/EMA منطقی است. "
            "لانگ خلاف روند بلندمدت — پرریسک."
        )
        counter = False

    confidence = int(np.mean([daily.score, h4.score, h1.score]))

    # H1 must not strongly oppose
    if bias == "long" and h1.trend == Trend.BEARISH:
        confidence -= 15
    if bias == "short" and h1.trend == Trend.BULLISH:
        confidence -= 15

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
        counter_trend=counter,
    )


def _trend_fa(trend: Trend) -> str:
    return {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[trend.value]


def build_report(daily_df: pd.DataFrame, h4_df: pd.DataFrame, h1_df: pd.DataFrame, generated_at: str) -> MarketReport:
    daily = analyze_timeframe(daily_df, "1d", "روزانه")
    h4 = analyze_timeframe(h4_df, "4h", "۴ ساعته", align_with=daily.trend)
    h1 = analyze_timeframe(h1_df, "1h", "۱ ساعته", align_with=daily.trend)

    allowed = _allowed_bias_from_daily(daily.trend)
    scenario = _build_scenario(daily, h4, h1)
    quality = int(np.mean([daily.score, h4.score, h1.score]))

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

    if scenario and scenario.confidence >= 70 and not daily.is_ranging:
        action = "full"
        summary.append("✅ شرایط مناسب برای سناریو ورود")
    elif scenario and scenario.confidence >= 50:
        action = "watch"
        summary.append("👀 نظارت — هنوز ورود قطعی نیست")
    elif daily.is_ranging or h4.is_ranging:
        action = "wait"
        summary.append("⏸ بازار در رنج — صبر تا شکست سطح")
    else:
        action = "no_signal"
        summary.append("⏳ فعلاً سیگنال قوی نیست — صبر کن")

    return MarketReport(
        generated_at=generated_at,
        symbol="BTC/USD",
        daily=daily,
        h4=h4,
        h1=h1,
        allowed_bias=allowed,
        scenario=scenario,
        summary_lines=summary,
        quality_score=quality,
        action=action,
    )
