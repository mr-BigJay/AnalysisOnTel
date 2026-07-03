"""10-point quality checklist before issuing trade scenarios."""

from __future__ import annotations

from dataclasses import dataclass

from market.derivatives import DerivativesSnapshot
from market.types import Bias, TimeframeAnalysis, Trend


@dataclass
class ChecklistResult:
    score: int
    passed: int
    total: int
    items: list[tuple[str, bool, str]]


def run_checklist(
    daily: TimeframeAnalysis,
    h4: TimeframeAnalysis,
    h1: TimeframeAnalysis,
    bias: Bias,
    derivatives: DerivativesSnapshot,
) -> ChecklistResult:
    items: list[tuple[str, bool, str]] = []

    # 1) Daily trend defined
    ok = daily.trend != Trend.NEUTRAL
    items.append(("روند روزانه مشخص است", ok, _trend_note(daily.trend)))

    # 2) 4H aligned with daily
    ok = daily.trend == Trend.NEUTRAL or h4.trend in (Trend.NEUTRAL, daily.trend)
    items.append(("۴H با روزانه هم‌جهت است", ok, f"۴H={h4.trend.value}"))

    # 3) 1H aligned with daily
    ok = daily.trend == Trend.NEUTRAL or h1.trend in (Trend.NEUTRAL, daily.trend)
    items.append(("۱H با روزانه هم‌جهت است", ok, f"۱H={h1.trend.value}"))

    # 4) Not ranging on 4H
    ok = not h4.is_ranging
    items.append(("بازار ۴H در رنج نیست", ok, "رنج" if h4.is_ranging else "روند/نوسان"))

    # 5) Volume confirmation on 4H
    ok = h4.volume_ratio >= 0.9
    items.append(("حجم ۴H کافی است", ok, f"نسبت حجم={h4.volume_ratio}"))

    # 6) RSI not in danger zone for proposed bias
    ok = _rsi_ok(bias, h4.rsi)
    items.append(("RSI در ناحیه مناسب", ok, f"RSI={h4.rsi}"))

    # 7) MACD supports direction on 4H
    ok = _macd_ok(bias, h4.macd_hist)
    items.append(("MACD هم‌جهت است", ok, f"MACD={h4.macd_hist:+.1f}"))

    # 8) Derivatives not opposing
    ok = _derivatives_ok(bias, derivatives)
    items.append(("مشتقات مخالف نیست", ok, _deriv_note(derivatives)))

    # 9) No extreme sentiment against trade
    ok = _sentiment_ok(bias, derivatives)
    items.append(("احساسات افراطی نیست", ok, _fng_note(derivatives)))

    # 10) Invalidation level exists (always true if levels computed)
    ok = h4.support > 0 and h4.resistance > 0
    items.append(("سطوح SL/TP قابل تعریف است", ok, "تعریف شد"))

    passed = sum(1 for _, ok, _ in items if ok)
    score = int(round(passed / len(items) * 100))
    return ChecklistResult(score=score, passed=passed, total=len(items), items=items)


def _trend_note(trend: Trend) -> str:
    return trend.value


def _rsi_ok(bias: Bias, rsi_val: float) -> bool:
    if bias == "long":
        return rsi_val < 68
    if bias == "short":
        return rsi_val > 32
    return True


def _macd_ok(bias: Bias, macd_hist: float) -> bool:
    if bias == "long":
        return macd_hist > -50
    if bias == "short":
        return macd_hist < 50
    return True


def _derivatives_ok(bias: Bias, d: DerivativesSnapshot) -> bool:
    if d.funding_rate is None:
        return True
    if bias == "long" and d.funding_rate > 0.0003:
        return False
    if bias == "short" and d.funding_rate < -0.0003:
        return False
    if d.long_short_ratio is None:
        return True
    if bias == "long" and d.long_short_ratio > 2.2:
        return False
    if bias == "short" and d.long_short_ratio < 0.7:
        return False
    return True


def _sentiment_ok(bias: Bias, d: DerivativesSnapshot) -> bool:
    if d.fear_greed_value is None:
        return True
    if bias == "long" and d.fear_greed_value > 78:
        return False
    if bias == "short" and d.fear_greed_value < 22:
        return False
    return True


def _deriv_note(d: DerivativesSnapshot) -> str:
    parts = []
    if d.funding_rate is not None:
        parts.append(f"FR={d.funding_rate*100:.3f}%")
    if d.long_short_ratio is not None:
        parts.append(f"L/S={d.long_short_ratio:.2f}")
    return " | ".join(parts) if parts else "N/A"


def _fng_note(d: DerivativesSnapshot) -> str:
    if d.fear_greed_value is None:
        return "N/A"
    return f"{d.fear_greed_value} ({d.fear_greed_label})"
