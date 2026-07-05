"""Decision engine: probability, confirmations, trade plan."""

from __future__ import annotations

from analysis.ict import ICTAnalysis
from analysis.liquidity import LiquidityAnalysis
from analysis.macro import MacroAnalysis
from analysis.models import TradeSetup
from analysis.orderflow import OrderFlowAnalysis
from analysis.structure import StructureAnalysis
from analysis.wyckoff import WyckoffAnalysis
from config import MAX_LEVERAGE, MAX_RISK_PCT


def score_probability(
    struct: StructureAnalysis,
    liq: LiquidityAnalysis,
    ict: ICTAnalysis,
    wyck: WyckoffAnalysis,
    flow: OrderFlowAnalysis,
    macro: MacroAnalysis,
    struct_daily: StructureAnalysis,
) -> tuple[int, int, str, int]:
    bull = 0
    bear = 0

    for src in (struct, struct_daily, liq, ict, wyck, flow, macro):
        if src.bullish:
            bull += 1
        if src.bearish:
            bear += 1

    if liq.bsl and not liq.bearish:
        bear += 1  # price below BSL magnet — sweep up then down scenario
    if liq.ssl and not liq.bullish:
        bull += 1

    total = bull + bear
    if total == 0:
        return 52, 48, "Neutral", 45

    bull_pct = round(bull / total * 100)
    bear_pct = 100 - bull_pct
    if bull_pct == 50:
        bull_pct, bear_pct = 53, 47

    if bull_pct > bear_pct + 15:
        bias = "Bullish"
    elif bear_pct > bull_pct + 15:
        bias = "Bearish"
    else:
        bias = "Neutral"

    spread = abs(bull_pct - bear_pct)
    confidence = min(95, 50 + spread + min(bull, bear) * 3)
    return bull_pct, bear_pct, bias, confidence


def count_confirmations(
    struct: StructureAnalysis,
    liq: LiquidityAnalysis,
    flow: OrderFlowAnalysis,
    macro: MacroAnalysis,
    wyck: WyckoffAnalysis,
    ict: ICTAnalysis,
) -> dict[str, bool]:
    return {
        "liquidity": bool(liq.bsl or liq.ssl or liq.sweeps),
        "structure": struct.trend in ("Bullish", "Bearish") and bool(struct.events or struct.pattern),
        "volume": "spike" in flow.volume_note.lower() or "normal" in flow.volume_note.lower(),
        "open_interest": "unavailable" not in flow.oi_note.lower(),
        "funding": "unavailable" not in flow.funding_note.lower(),
        "macro": not macro.risky or bool(macro.headlines),
        "ict_zone": "Premium" in ict.zone or "Discount" in ict.zone,
        "wyckoff": wyck.phase not in ("Re-accumulation / Re-distribution",),
    }


def stars_from_confidence(confidence: int) -> int:
    if confidence >= 85:
        return 5
    if confidence >= 75:
        return 4
    if confidence >= 65:
        return 3
    if confidence >= 55:
        return 2
    return 1


def build_trade_setup(
    verdict: str,
    price: float,
    liq: LiquidityAnalysis,
    ict: ICTAnalysis,
    struct: StructureAnalysis,
    atr: float,
) -> TradeSetup | None:
    if verdict not in ("LONG", "SHORT"):
        return None

    if verdict == "LONG":
        if ict.ote_zone:
            entry_low, entry_high = ict.ote_zone
        elif liq.ssl:
            entry_low = liq.ssl[0] * 0.998
            entry_high = liq.ssl[0] * 1.003
        else:
            entry_low = price * 0.985
            entry_high = price * 0.995
        sl = entry_low - atr * 1.2
        risk = entry_high - sl
        tp1 = entry_high + risk * 1.5
        tp2 = entry_high + risk * 2.5
        tp3 = liq.bsl[0] if liq.bsl else entry_high + risk * 4
        style = "Swing" if struct.trend == "Bullish" else "Intraday"
        reason = "Discount zone + SSL reaction / bullish structure alignment"
        invalidation = f"Close below ${sl:,.0f} on 4H"
    else:
        if liq.bsl:
            entry_low = liq.bsl[-1] * 0.997
            entry_high = liq.bsl[-1] * 1.005
        else:
            entry_low = price * 1.005
            entry_high = price * 1.015
        sl = entry_high + atr * 1.2
        risk = sl - entry_low
        tp1 = entry_low - risk * 1.5
        tp2 = entry_low - risk * 2.5
        tp3 = liq.ssl[0] if liq.ssl else entry_low - risk * 4
        style = "Intraday" if "Premium" in ict.zone else "Swing"
        reason = "Premium zone + BSL sweep scenario / bearish structure"
        invalidation = f"Close above ${sl:,.0f} on 4H"

    rr = abs(tp1 - entry_high) / max(abs(entry_high - sl), 1)
    lev = min(MAX_LEVERAGE, 10 if style == "Swing" else 5)

    return TradeSetup(
        entry_low=round(entry_low, 0),
        entry_high=round(entry_high, 0),
        stop_loss=round(sl, 0),
        tp1=round(tp1, 0),
        tp2=round(tp2, 0),
        tp3=round(tp3, 0),
        risk_reward=round(rr, 2),
        leverage=lev,
        style=style,
        invalidation=invalidation,
        reason=reason,
    )


def decide_verdict(
    bias: str,
    bull_pct: int,
    bear_pct: int,
    confirmations: dict[str, bool],
    macro: MacroAnalysis,
) -> str:
    count = sum(1 for v in confirmations.values() if v)
    core = sum(
        1
        for k in ("liquidity", "structure", "volume", "open_interest", "funding", "macro")
        if confirmations.get(k)
    )

    if core < 5:
        return "WAIT"

    if macro.risky and count < 6:
        return "NO TRADE"

    if (bias == "Bullish" or bull_pct >= 62) and bull_pct >= 58:
        return "LONG"
    if (bias == "Bearish" or bear_pct >= 62) and bear_pct >= 58:
        return "SHORT"

    return "WAIT"
