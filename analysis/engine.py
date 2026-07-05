"""Institutional analysis orchestrator."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from analysis.decision import (
    build_trade_setup,
    count_confirmations,
    decide_verdict,
    score_probability,
    stars_from_confidence,
)
from analysis.ict import analyze_ict, ict_dict
from analysis.liquidity import analyze_liquidity, liquidity_dict
from analysis.macro import analyze_macro, macro_dict
from analysis.models import InstitutionalReport
from analysis.orderflow import analyze_orderflow, orderflow_dict
from analysis.structure import analyze_structure, structure_dict
from analysis.wyckoff import analyze_wyckoff, wyckoff_dict
from config import ANALYSIS_TIMEFRAMES, HISTORY_PATH, REPORT_PATH
from market.data import closed_candles, fetch_ohlcv
from market.derivatives import fetch_derivatives

logger = logging.getLogger(__name__)


def _atr(df, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = (high - low).combine((high - close.shift()).abs(), max).combine((low - close.shift()).abs(), max)
    return float(tr.rolling(period).mean().iloc[-1] or (high.iloc[-1] - low.iloc[-1]))


def run_analysis() -> InstitutionalReport:
    dfs: dict = {}
    for tf in ANALYSIS_TIMEFRAMES:
        try:
            dfs[tf] = closed_candles(fetch_ohlcv(tf))
        except Exception:
            logger.warning("Failed to fetch %s", tf)
    if "4h" not in dfs or "1h" not in dfs or "1d" not in dfs:
        raise RuntimeError("Required OHLCV data unavailable")
    if "1w" not in dfs:
        dfs["1w"] = dfs["1d"]
    deriv = fetch_derivatives()

    df_4h = dfs["4h"]
    df_1h = dfs["1h"]
    df_1d = dfs["1d"]
    df_1w = dfs.get("1w", df_1d)
    price = float(df_1h["Close"].iloc[-1])

    struct_4h = analyze_structure(df_4h, "4H")
    struct_1d = analyze_structure(df_1d, "1D")
    struct_1w = analyze_structure(df_1w, "1W")

    liq = analyze_liquidity(df_4h, price)
    ict = analyze_ict(df_1h, df_1d, df_1w, price, struct_1d.trend, struct_1w.trend)
    wyck = analyze_wyckoff(df_4h, price)
    flow = analyze_orderflow(df_4h, deriv)
    macro = analyze_macro(deriv)

    bull_pct, bear_pct, bias, confidence = score_probability(
        struct_4h, liq, ict, wyck, flow, macro, struct_1d
    )
    confirmations = count_confirmations(struct_4h, liq, flow, macro, wyck, ict)
    conf_count = sum(1 for v in confirmations.values() if v)
    verdict = decide_verdict(bias, bull_pct, bear_pct, confirmations, macro)
    stars = stars_from_confidence(confidence)
    atr_val = _atr(df_4h)
    trade = build_trade_setup(verdict, price, liq, ict, struct_4h, atr_val)

    narrative = _build_narrative(
        price, bias, verdict, struct_4h, liq, ict, wyck, flow, macro, bull_pct, bear_pct, conf_count
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = InstitutionalReport(
        generated_at=now,
        price=price,
        bias=bias,
        stars=stars,
        confidence=confidence,
        bullish_pct=bull_pct,
        bearish_pct=bear_pct,
        verdict=verdict,
        liquidity=liquidity_dict(liq),
        structure={
            "4h": structure_dict(struct_4h),
            "1d": structure_dict(struct_1d),
            "1w": structure_dict(struct_1w),
        },
        ict=ict_dict(ict),
        wyckoff=wyckoff_dict(wyck),
        orderflow=orderflow_dict(flow),
        macro=macro_dict(macro),
        confirmations=confirmations,
        confirmation_count=conf_count,
        trade=trade,
        narrative=narrative,
        sections={
            "liquidity": liq.summary,
            "structure": struct_4h.summary + " " + struct_1d.summary,
            "ict": ict.summary,
            "orderflow": flow.summary,
            "macro": macro.summary,
            "wyckoff": wyck.summary,
        },
    )
    return report


def _build_narrative(
    price, bias, verdict, struct, liq, ict, wyck, flow, macro, bull_pct, bear_pct, conf_count
) -> str:
    parts = [
        f"BTC at ${price:,.0f}. Institutional bias: {bias} ({bull_pct}% bull / {bear_pct}% bear).",
        f"4H structure {struct.trend} ({struct.pattern}). Wyckoff: {wyck.phase}.",
        ict.zone,
        flow.volume_note,
    ]
    if liq.sweeps:
        parts.append(liq.sweeps[0])
    parts.append(f"{conf_count}/8 confirmations. Verdict: {verdict}.")
    if verdict == "WAIT":
        parts.append("Insufficient confluence — respect liquidity, wait for displacement.")
    elif verdict == "NO TRADE":
        parts.append("Macro risk elevated — stand aside.")
    else:
        parts.append("Trade only at premium/discount with structure confirmation. Never chase.")
    return " ".join(parts)


def save_report(report: InstitutionalReport) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    history: list = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    history.insert(0, {"generated_at": report.generated_at, "verdict": report.verdict, "price": report.price, "bias": report.bias})
    HISTORY_PATH.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")


def load_report() -> dict | None:
    if not REPORT_PATH.exists():
        return None
    try:
        return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
