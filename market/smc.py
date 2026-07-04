"""SMC/ICT signals: liquidity grab, MSS, level break, breakout retest."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from market.levels import find_key_levels, nearest_support_resistance


class GrabKind(str, Enum):
    BULLISH = "bullish"  # buy-side liquidity sweep
    BEARISH = "bearish"  # sell-side liquidity sweep


class MssKind(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class LiquidityGrab:
    kind: GrabKind
    timeframe: str
    swept_level: float
    close: float
    candle_ts: int
    fingerprint: str
    note: str


@dataclass
class MarketStructureShift:
    kind: MssKind
    timeframe: str
    break_level: float
    close: float
    candle_ts: int
    fingerprint: str
    note: str


@dataclass
class LevelBreak:
    direction: str  # up | down
    timeframe: str
    level: float
    close: float
    candle_ts: int
    fingerprint: str


@dataclass
class RetestZone:
    direction: str  # long | short
    timeframe: str
    entry_low: float
    entry_high: float
    stop_loss: float
    breakout_level: float
    candle_ts: int
    fingerprint: str


def _closed(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1] if len(df) > 1 else df


def _swing_highs(high: pd.Series, window: int = 3) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    vals = high.values
    for i in range(window, len(high) - window):
        seg = vals[i - window : i + window + 1]
        if vals[i] == seg.max():
            out.append((i, float(vals[i])))
    return out


def _swing_lows(low: pd.Series, window: int = 3) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    vals = low.values
    for i in range(window, len(low) - window):
        seg = vals[i - window : i + window + 1]
        if vals[i] == seg.min():
            out.append((i, float(vals[i])))
    return out


def detect_liquidity_grab(
    df: pd.DataFrame,
    timeframe: str,
    lookback: int = 40,
    swing_window: int = 3,
    sweep_pct: float = 0.0015,
) -> LiquidityGrab | None:
    """Sweep of swing high/low with close back inside (last closed candle)."""
    closed = _closed(df)
    if len(closed) < lookback + 5:
        return None

    seg = closed.tail(lookback)
    i = len(seg) - 1
    bar = seg.iloc[i]
    highs = _swing_highs(seg["High"].iloc[:-1], swing_window)
    lows = _swing_lows(seg["Low"].iloc[:-1], swing_window)

    ts = int(seg.index[i].timestamp())
    close = float(bar["Close"])
    high = float(bar["High"])
    low = float(bar["Low"])

    if highs:
        swing_h = highs[-1][1]
        if high > swing_h * (1 + sweep_pct) and close < swing_h:
            return LiquidityGrab(
                kind=GrabKind.BEARISH,
                timeframe=timeframe,
                swept_level=swing_h,
                close=close,
                candle_ts=ts,
                fingerprint=f"grab_bear_{timeframe}_{ts}_{swing_h:.0f}",
                note=f"سقف {_fmt(swing_h)} جمع شد و کندل پایین آن بست",
            )

    if lows:
        swing_l = lows[-1][1]
        if low < swing_l * (1 - sweep_pct) and close > swing_l:
            return LiquidityGrab(
                kind=GrabKind.BULLISH,
                timeframe=timeframe,
                swept_level=swing_l,
                close=close,
                candle_ts=ts,
                fingerprint=f"grab_bull_{timeframe}_{ts}_{swing_l:.0f}",
                note=f"کف {_fmt(swing_l)} جمع شد و کندل بالای آن بست",
            )
    return None


def _fmt(p: float) -> str:
    return f"${p:,.0f}"


def detect_mss(
    df: pd.DataFrame,
    timeframe: str,
    lookback: int = 50,
    swing_window: int = 3,
) -> MarketStructureShift | None:
    """
    Bullish MSS: break above last lower-high (shift from bearish structure).
    Bearish MSS: break below last higher-low (shift from bullish structure).
    """
    closed = _closed(df)
    if len(closed) < lookback + 5:
        return None

    seg = closed.tail(lookback)
    highs = _swing_highs(seg["High"], swing_window)
    lows = _swing_lows(seg["Low"], swing_window)
    if len(highs) < 2 or len(lows) < 2:
        return None

    close = float(seg["Close"].iloc[-1])
    prev_close = float(seg["Close"].iloc[-2])
    ts = int(seg.index[-1].timestamp())

    # Lower-high = high that is lower than previous swing high
    if len(highs) >= 2:
        lh = highs[-1][1]
        if prev_close <= lh < close:
            return MarketStructureShift(
                kind=MssKind.BULLISH,
                timeframe=timeframe,
                break_level=lh,
                close=close,
                candle_ts=ts,
                fingerprint=f"mss_bull_{timeframe}_{ts}_{lh:.0f}",
                note=f"شکست LH در {_fmt(lh)} — MSS صعودی",
            )

    if len(lows) >= 2:
        hl = lows[-1][1]
        if prev_close >= hl > close:
            return MarketStructureShift(
                kind=MssKind.BEARISH,
                timeframe=timeframe,
                break_level=hl,
                close=close,
                candle_ts=ts,
                fingerprint=f"mss_bear_{timeframe}_{ts}_{hl:.0f}",
                note=f"شکست HL در {_fmt(hl)} — MSS نزولی",
            )
    return None


def detect_level_break(
    df: pd.DataFrame,
    timeframe: str,
) -> LevelBreak | None:
    """Close breaks nearest support/resistance (closed candles)."""
    closed = _closed(df)
    if len(closed) < 30:
        return None

    hist = closed.iloc[:-1]
    last = closed.iloc[-1]
    price = float(last["Close"])
    prev = float(closed.iloc[-2]["Close"])
    supports, resistances = find_key_levels(hist)
    support, resistance = nearest_support_resistance(float(hist["Close"].iloc[-1]), supports, resistances)
    ts = int(closed.index[-1].timestamp())

    if prev <= resistance < price:
        return LevelBreak(
            direction="up",
            timeframe=timeframe,
            level=resistance,
            close=price,
            candle_ts=ts,
            fingerprint=f"break_up_{timeframe}_{ts}_{resistance:.0f}",
        )
    if prev >= support > price:
        return LevelBreak(
            direction="down",
            timeframe=timeframe,
            level=support,
            close=price,
            candle_ts=ts,
            fingerprint=f"break_down_{timeframe}_{ts}_{support:.0f}",
        )
    return None


def compute_retest_zone(
    df: pd.DataFrame,
    timeframe: str,
) -> RetestZone | None:
    """After bullish/bearish break on prior candle, define retest entry zone."""
    closed = _closed(df)
    if len(closed) < 30:
        return None

    brk = detect_level_break(df, timeframe)
    if not brk:
        return None

    level = brk.level
    if brk.direction == "up":
        return RetestZone(
            direction="long",
            timeframe=timeframe,
            entry_low=round(level * 0.997, 1),
            entry_high=round(level * 1.002, 1),
            stop_loss=round(level * 0.992, 1),
            breakout_level=level,
            candle_ts=brk.candle_ts,
            fingerprint=f"retest_long_{timeframe}_{brk.candle_ts}_{level:.0f}",
        )
    return RetestZone(
        direction="short",
        timeframe=timeframe,
        entry_low=round(level * 0.998, 1),
        entry_high=round(level * 1.003, 1),
        stop_loss=round(level * 1.008, 1),
        breakout_level=level,
        candle_ts=brk.candle_ts,
        fingerprint=f"retest_short_{timeframe}_{brk.candle_ts}_{level:.0f}",
    )


def price_in_retest_zone(zone: RetestZone, price: float) -> bool:
    return zone.entry_low <= price <= zone.entry_high
