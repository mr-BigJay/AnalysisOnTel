"""Support/resistance level detection."""

from __future__ import annotations

import numpy as np
import pandas as pd


def find_key_levels(df: pd.DataFrame, window: int = 5, clusters: int = 3) -> tuple[list[float], list[float]]:
    """Return clustered support and resistance levels from swing points."""
    highs = df["High"].values
    lows = df["Low"].values
    resistance: list[float] = []
    support: list[float] = []

    for i in range(window, len(df) - window):
        segment_h = highs[i - window : i + window + 1]
        segment_l = lows[i - window : i + window + 1]
        if highs[i] == segment_h.max():
            resistance.append(float(highs[i]))
        if lows[i] == segment_l.min():
            support.append(float(lows[i]))

    return _cluster_levels(support, clusters), _cluster_levels(resistance, clusters)


def _cluster_levels(levels: list[float], max_levels: int, tolerance: float = 0.006) -> list[float]:
    if not levels:
        return []
    levels = sorted(levels)
    groups: list[list[float]] = [[levels[0]]]
    for level in levels[1:]:
        if abs(level - groups[-1][-1]) / groups[-1][-1] <= tolerance:
            groups[-1].append(level)
        else:
            groups.append([level])
    merged = [float(np.mean(g)) for g in groups]
    return merged[-max_levels:]


def nearest_support_resistance(price: float, supports: list[float], resistances: list[float]) -> tuple[float, float]:
    below = [s for s in supports if s <= price * 1.002]
    above = [r for r in resistances if r >= price * 0.998]
    support = max(below) if below else (min(supports) if supports else price * 0.97)
    resistance = min(above) if above else (max(resistances) if resistances else price * 1.03)
    return support, resistance
