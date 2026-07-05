"""Wyckoff phase detection."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class WyckoffAnalysis:
    phase: str
    event: str | None
    summary: str
    bullish: bool
    bearish: bool


def analyze_wyckoff(df: pd.DataFrame, price: float) -> WyckoffAnalysis:
    r50 = df.tail(50)
    r20 = df.tail(20)
    range50 = (float(r50["High"].max()) - float(r50["Low"].min())) / price * 100
    range20 = (float(r20["High"].max()) - float(r20["Low"].min())) / price * 100
    vol = df["Volume"]
    vol_declining = float(vol.tail(10).mean()) < float(vol.tail(30).mean()) * 0.85
    mid = (float(r50["High"].max()) + float(r50["Low"].min())) / 2
    near_high = price > mid * 1.02
    near_low = price < mid * 0.98

    last = df.iloc[-1]
    spring = float(last["Low"]) < float(r20["Low"].min()) * 1.001 and float(last["Close"]) > float(
        r20["Low"].min()
    )
    upthrust = float(last["High"]) > float(r20["High"].max()) * 0.999 and float(last["Close"]) < float(
        r20["High"].max()
    )

    if range20 < range50 * 0.65 and vol_declining and near_low:
        phase, bullish, bearish = "Accumulation", True, False
    elif range20 < range50 * 0.65 and vol_declining and near_high:
        phase, bullish, bearish = "Distribution", False, True
    elif price > float(r50["Close"].iloc[0]) * 1.03:
        phase, bullish, bearish = "Markup", True, False
    elif price < float(r50["Close"].iloc[0]) * 0.97:
        phase, bullish, bearish = "Markdown", False, True
    else:
        phase, bullish, bearish = "Re-accumulation / Re-distribution", False, False

    event = None
    if spring:
        event = "Spring detected — composite operator absorption"
        bullish = True
    if upthrust:
        event = "Upthrust detected — supply entering"
        bearish = True

    summary = f"Wyckoff phase: {phase}."
    if event:
        summary += f" {event}."
    if vol_declining:
        summary += " Volume contracting — smart money patience."

    return WyckoffAnalysis(phase, event, summary, bullish, bearish)


def wyckoff_dict(w: WyckoffAnalysis) -> dict:
    return {"phase": w.phase, "event": w.event, "summary": w.summary}
