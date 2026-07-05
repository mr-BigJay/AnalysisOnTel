"""ICT: Order Blocks, FVG, Premium/Discount, OTE, bias."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ICTAnalysis:
    order_blocks: list[dict]
    fvgs: list[dict]
    zone: str
    ote_zone: tuple[float, float] | None
    daily_bias: str
    weekly_bias: str
    kill_zone: str
    summary: str
    bullish: bool
    bearish: bool


def _find_fvgs(df: pd.DataFrame, lookback: int = 30) -> list[dict]:
    fvgs: list[dict] = []
    seg = df.tail(lookback)
    for i in range(2, len(seg)):
        c0, c2 = seg.iloc[i - 2], seg.iloc[i]
        if float(c2["Low"]) > float(c0["High"]):
            fvgs.append(
                {
                    "type": "Bullish FVG",
                    "low": float(c0["High"]),
                    "high": float(c2["Low"]),
                }
            )
        if float(c2["High"]) < float(c0["Low"]):
            fvgs.append(
                {
                    "type": "Bearish FVG",
                    "low": float(c2["High"]),
                    "high": float(c0["Low"]),
                }
            )
    return fvgs[-4:]


def _find_order_blocks(df: pd.DataFrame, lookback: int = 40) -> list[dict]:
    obs: list[dict] = []
    seg = df.tail(lookback)
    for i in range(1, len(seg) - 2):
        cur, nxt = seg.iloc[i], seg.iloc[i + 1]
        body_cur = abs(float(cur["Close"]) - float(cur["Open"]))
        body_nxt = abs(float(nxt["Close"]) - float(nxt["Open"]))
        if body_nxt > body_cur * 2:
            if float(nxt["Close"]) > float(nxt["Open"]) and float(cur["Close"]) < float(cur["Open"]):
                obs.append(
                    {
                        "type": "Bullish OB",
                        "low": float(cur["Low"]),
                        "high": float(cur["High"]),
                    }
                )
            elif float(nxt["Close"]) < float(nxt["Open"]) and float(cur["Close"]) > float(cur["Open"]):
                obs.append(
                    {
                        "type": "Bearish OB",
                        "low": float(cur["Low"]),
                        "high": float(cur["High"]),
                    }
                )
    return obs[-3:]


def _kill_zone() -> str:
    from datetime import datetime, timezone

    h = datetime.now(timezone.utc).hour
    if 7 <= h < 10:
        return "London Kill Zone (active)"
    if 12 <= h < 15:
        return "NY AM Kill Zone (active)"
    if 19 <= h < 22:
        return "NY PM Kill Zone (active)"
    return "Outside kill zones"


def analyze_ict(
    df_entry: pd.DataFrame,
    df_daily: pd.DataFrame,
    df_weekly: pd.DataFrame,
    price: float,
    struct_daily: str,
    struct_weekly: str,
) -> ICTAnalysis:
    rh = float(df_entry["High"].tail(50).max())
    rl = float(df_entry["Low"].tail(50).min())
    eq = (rh + rl) / 2
    rng = rh - rl

    if price > eq + rng * 0.1:
        zone = "Premium — favor shorts / wait for discount"
        bearish = True
        bullish = False
    elif price < eq - rng * 0.1:
        zone = "Discount — favor longs / sell premium"
        bullish = True
        bearish = False
    else:
        zone = "Equilibrium — no edge until displacement"
        bullish = bearish = False

    ote = None
    if rng > 0:
        if struct_daily == "Bullish":
            ote = (rl + rng * 0.62, rl + rng * 0.79)
        elif struct_daily == "Bearish":
            ote = (rh - rng * 0.79, rh - rng * 0.62)

    obs = _find_order_blocks(df_entry)
    fvgs = _find_fvgs(df_entry)

    summary = f"{zone}. Dealing range ${rl:,.0f}–${rh:,.0f}."
    if obs:
        summary += f" Nearest OB: {obs[-1]['type']} ${obs[-1]['low']:,.0f}–${obs[-1]['high']:,.0f}."
    if fvgs:
        f = fvgs[-1]
        summary += f" Active {f['type']} ${f['low']:,.0f}–${f['high']:,.0f}."

    return ICTAnalysis(
        obs,
        fvgs,
        zone,
        ote,
        struct_daily,
        struct_weekly,
        _kill_zone(),
        summary,
        bullish,
        bearish,
    )


def ict_dict(i: ICTAnalysis) -> dict:
    return {
        "order_blocks": i.order_blocks,
        "fvgs": i.fvgs,
        "premium_discount": i.zone,
        "ote": list(i.ote_zone) if i.ote_zone else None,
        "daily_bias": i.daily_bias,
        "weekly_bias": i.weekly_bias,
        "kill_zone": i.kill_zone,
        "summary": i.summary,
    }
