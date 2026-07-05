"""Liquidity: BSL, SSL, equal highs/lows, sweeps."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class LiquidityAnalysis:
    bsl: list[float]
    ssl: list[float]
    equal_highs: list[float]
    equal_lows: list[float]
    sweeps: list[str]
    summary: str
    bullish: bool
    bearish: bool


def _cluster(levels: list[float], tol: float = 0.003) -> list[float]:
    if not levels:
        return []
    levels = sorted(levels)
    groups: list[list[float]] = [[levels[0]]]
    for lv in levels[1:]:
        if abs(lv - groups[-1][-1]) / groups[-1][-1] <= tol:
            groups[-1].append(lv)
        else:
            groups.append([lv])
    return [sum(g) / len(g) for g in groups]


def _swing_highs(df: pd.DataFrame, w: int = 3) -> list[float]:
    out: list[float] = []
    h = df["High"].values
    for i in range(w, len(df) - w):
        if h[i] == h[i - w : i + w + 1].max():
            out.append(float(h[i]))
    return out


def _swing_lows(df: pd.DataFrame, w: int = 3) -> list[float]:
    out: list[float] = []
    lo = df["Low"].values
    for i in range(w, len(df) - w):
        if lo[i] == lo[i - w : i + w + 1].min():
            out.append(float(lo[i]))
    return out


def analyze_liquidity(df: pd.DataFrame, price: float) -> LiquidityAnalysis:
    highs = _swing_highs(df)
    lows = _swing_lows(df)
    bsl = sorted([h for h in _cluster(highs) if h > price * 1.001])[:3]
    ssl = sorted([l for l in _cluster(lows) if l < price * 0.999], reverse=True)[:3]

    eq_highs = [h for h in _cluster(highs) if len([x for x in highs if abs(x - h) / h < 0.003]) >= 2]
    eq_lows = [l for l in _cluster(lows) if len([x for x in lows if abs(x - l) / l < 0.003]) >= 2]

    sweeps: list[str] = []
    last = df.iloc[-1]
    prev = df.iloc[-2]
    hi, lo, cl = float(last["High"]), float(last["Low"]), float(last["Close"])

    if bsl:
        top = bsl[0]
        if hi > top and cl < top:
            sweeps.append(f"BSL sweep at ${top:,.0f} — sell-side reaction likely")
    if ssl:
        bot = ssl[0]
        if lo < bot and cl > bot:
            sweeps.append(f"SSL sweep at ${bot:,.0f} — buy-side reaction likely")

    bullish = any("SSL sweep" in s for s in sweeps)
    bearish = any("BSL sweep" in s for s in sweeps)

    internal = f"Internal range ${min(ssl + [price]):,.0f}–${max(bsl + [price]):,.0f}"
    summary = (
        f"BSL: {', '.join(f'${x:,.0f}' for x in bsl) or '—'}. "
        f"SSL: {', '.join(f'${x:,.0f}' for x in ssl) or '—'}. "
        f"{internal}."
    )
    if eq_highs:
        summary += f" Equal highs at ${eq_highs[0]:,.0f} (liquidity magnet)."
    if eq_lows:
        summary += f" Equal lows at ${eq_lows[0]:,.0f}."
    if sweeps:
        summary += " " + " ".join(sweeps)

    return LiquidityAnalysis(bsl, ssl, eq_highs[:2], eq_lows[:2], sweeps, summary, bullish, bearish)


def liquidity_dict(l: LiquidityAnalysis) -> dict:
    return {
        "bsl": l.bsl,
        "ssl": l.ssl,
        "equal_highs": l.equal_highs,
        "equal_lows": l.equal_lows,
        "sweeps": l.sweeps,
        "summary": l.summary,
    }
