"""Order flow: volume, OI, funding, positioning."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from market.derivatives import DerivativesSnapshot


@dataclass
class OrderFlowAnalysis:
    volume_note: str
    oi_note: str
    funding_note: str
    positioning_note: str
    summary: str
    bullish: bool
    bearish: bool


def analyze_orderflow(df: pd.DataFrame, deriv: DerivativesSnapshot) -> OrderFlowAnalysis:
    vol = df["Volume"]
    ratio = float(vol.iloc[-1]) / float(vol.tail(20).mean()) if float(vol.tail(20).mean()) else 1
    price_up = float(df["Close"].iloc[-1]) > float(df["Close"].iloc[-5])

    if ratio >= 1.8 and price_up:
        vol_note = f"Volume spike {ratio:.1f}x — bullish participation"
        vol_bull, vol_bear = True, False
    elif ratio >= 1.8 and not price_up:
        vol_note = f"Volume spike {ratio:.1f}x on decline — distribution"
        vol_bull, vol_bear = False, True
    elif ratio < 0.7:
        vol_note = f"Volume contracted {ratio:.1f}x — lack of conviction"
        vol_bull = vol_bear = False
    else:
        vol_note = f"Volume normal ({ratio:.1f}x avg)"
        vol_bull = vol_bear = False

    oi_bull = oi_bear = False
    if deriv.open_interest_usd:
        b = deriv.open_interest_usd / 1e9
        oi_note = f"OI ${b:.2f}B — elevated leverage in system"
        if price_up:
            oi_note += " (OI + price up = new longs)"
            oi_bull = True
        else:
            oi_note += " (OI + price down = long liquidation or new shorts)"
            oi_bear = True
    else:
        oi_note = "OI data unavailable"

    fund_bull = fund_bear = False
    if deriv.funding_rate is not None:
        fr = deriv.funding_rate
        if fr >= 0.0003:
            funding_note = f"Funding {fr*100:.4f}% — crowded longs, squeeze risk"
            fund_bear = True
        elif fr <= -0.0001:
            funding_note = f"Funding {fr*100:.4f}% — shorts paying, squeeze potential"
            fund_bull = True
        else:
            funding_note = f"Funding {fr*100:.4f}% — neutral"
    else:
        funding_note = "Funding unavailable"

    pos_bull = pos_bear = False
    if deriv.long_short_ratio:
        ls = deriv.long_short_ratio
        if ls >= 1.5:
            positioning_note = f"L/S {ls:.2f} — long crowding (contrarian bearish)"
            pos_bear = True
        elif ls <= 0.75:
            positioning_note = f"L/S {ls:.2f} — short crowding (contrarian bullish)"
            pos_bull = True
        else:
            positioning_note = f"L/S {ls:.2f} — balanced"
    else:
        positioning_note = "L/S ratio unavailable"

    bullish = sum([vol_bull, oi_bull, fund_bull, pos_bull]) >= 2
    bearish = sum([vol_bear, oi_bear, fund_bear, pos_bear]) >= 2

    summary = f"{vol_note}. {oi_note}. {funding_note}. {positioning_note}."
    return OrderFlowAnalysis(vol_note, oi_note, funding_note, positioning_note, summary, bullish, bearish)


def orderflow_dict(o: OrderFlowAnalysis) -> dict:
    return {
        "volume": o.volume_note,
        "open_interest": o.oi_note,
        "funding": o.funding_note,
        "positioning": o.positioning_note,
        "summary": o.summary,
    }
