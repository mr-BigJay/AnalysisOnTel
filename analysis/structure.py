"""Market structure: HH/HL/LH/LL, BOS, MSS, CHoCH."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class StructureAnalysis:
    trend: str
    pattern: str
    events: list[str]
    summary: str
    bullish: bool
    bearish: bool


def _swings(series: pd.Series, window: int = 3) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    vals = series.values
    for i in range(window, len(series) - window):
        seg = vals[i - window : i + window + 1]
        if vals[i] == seg.max() if series.name == "High" else vals[i] == seg.min():
            out.append((i, float(vals[i])))
    return out


def analyze_structure(df: pd.DataFrame, label: str = "4H") -> StructureAnalysis:
    highs = _swings(df["High"].rename("High"))
    lows = _swings(df["Low"].rename("Low"))
    events: list[str] = []
    close = float(df["Close"].iloc[-1])

    if len(highs) < 2 or len(lows) < 2:
        return StructureAnalysis(
            "Neutral", "Insufficient data", [], f"{label}: not enough swings", False, False
        )

    h1, h2 = highs[-2][1], highs[-1][1]
    l1, l2 = lows[-2][1], lows[-1][1]

    hh = h2 > h1
    hl = l2 > l1
    lh = h2 < h1
    ll = l2 < l1

    if hh and hl:
        trend, pattern = "Bullish", "HH + HL"
        bullish, bearish = True, False
    elif lh and ll:
        trend, pattern = "Bearish", "LH + LL"
        bullish, bearish = False, True
    elif hh and ll:
        trend, pattern = "Expanding", "HH + LL (volatility expansion)"
        bullish, bearish = False, False
    elif lh and hl:
        trend, pattern = "Contracting", "LH + HL (compression)"
        bullish, bearish = False, False
    else:
        trend, pattern = "Neutral", "Mixed structure"
        bullish, bearish = False, False

    prev_close = float(df["Close"].iloc[-2])
    if close > h1 and prev_close <= h1:
        events.append(f"BOS Bullish above ${h1:,.0f}")
    if close < l1 and prev_close >= l1:
        events.append(f"BOS Bearish below ${l1:,.0f}")

    if trend == "Bearish" and close > h2:
        events.append(f"CHoCH Bullish — break above LH ${h2:,.0f}")
        bullish = True
    if trend == "Bullish" and close < l2:
        events.append(f"CHoCH Bearish — break below HL ${l2:,.0f}")
        bearish = True

    if trend == "Bullish" and close < l2:
        events.append(f"MSS Bearish — lost HL ${l2:,.0f}")
        bearish = True
    if trend == "Bearish" and close > h2:
        events.append(f"MSS Bullish — reclaimed LH ${h2:,.0f}")
        bullish = True

    summary = f"{label} structure: {pattern}. Trend {trend}. Price ${close:,.0f}."
    if events:
        summary += " Events: " + "; ".join(events[-3:]) + "."

    return StructureAnalysis(trend, pattern, events, summary, bullish, bearish)


def structure_dict(s: StructureAnalysis) -> dict:
    return {
        "trend": s.trend,
        "pattern": s.pattern,
        "events": s.events,
        "summary": s.summary,
    }
