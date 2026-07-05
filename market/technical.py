"""Comprehensive BTC technical analysis report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from config import TA_TIMEFRAMES, TIMEFRAME_LABELS
from market.data import fetch_ohlcv
from market.indicators import (
    adx,
    atr,
    bollinger_bands,
    ema,
    ichimoku,
    macd,
    parabolic_sar,
    rsi,
    sma,
    stochastic_rsi,
    supertrend,
    vwap,
)
from market.levels import find_key_levels, nearest_support_resistance


@dataclass
class TimeframeTA:
    key: str
    label: str
    price: float
    trend: str
    trend_note: str
    adx_val: float
    structure: str


@dataclass
class TechnicalReport:
    generated_at: str
    price: float
    timeframes: list[TimeframeTA]
    supports: list[float]
    resistances: list[float]
    nearest_support: float
    nearest_resistance: float
    price_action: str
    classic_pattern: str
    candle_pattern: str
    candle_tf: str
    volume_note: str
    indicators: list[tuple[str, str, str]]  # name, value, signal
    summary: str


def _closed(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1] if len(df) > 1 else df


def _trend_from_df(df: pd.DataFrame) -> tuple[str, str]:
    close = df["Close"]
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    c, e20v, e50v = float(close.iloc[-1]), float(e20.iloc[-1]), float(e50.iloc[-1])
    adx_val, plus_di, minus_di = adx(df)
    a = float(adx_val.iloc[-1]) if not pd.isna(adx_val.iloc[-1]) else 0

    if c > e20v > e50v:
        t = "صعودی 📈"
        note = f"قیمت بالای EMA20/50 — ADX={a:.0f}"
    elif c < e20v < e50v:
        t = "نزولی 📉"
        note = f"قیمت زیر EMA20/50 — ADX={a:.0f}"
    else:
        t = "خنثی/رنج ➖"
        note = f"میانگین‌ها نامشخص — ADX={a:.0f}"

    if a >= 25:
        note += " — روند قوی"
    elif a < 20:
        note += " — روند ضعیف/رنج"
    return t, note


def _market_structure(df: pd.DataFrame) -> str:
    recent = df.tail(30)
    highs = recent["High"].values
    lows = recent["Low"].values
    mid = len(recent) // 2
    h1, h2 = highs[:mid].max(), highs[mid:].max()
    l1, l2 = lows[:mid].min(), lows[mid:].min()

    if h2 > h1 and l2 > l1:
        return "ساختار صعودی (HH + HL)"
    if h2 < h1 and l2 < l1:
        return "ساختار نزولی (LH + LL)"
    return "ساختار مختلط / رنج"


def _classic_pattern(df: pd.DataFrame) -> str:
    r20 = df.tail(20)
    r50 = df.tail(50)
    range20 = (float(r20["High"].max()) - float(r20["Low"].min())) / float(r20["Close"].mean()) * 100
    range50 = (float(r50["High"].max()) - float(r50["Low"].min())) / float(r50["Close"].mean()) * 100

    if range20 < range50 * 0.6 and range20 < 4:
        return "فشردگی/مثلث — آماده شکست"
    if range20 > 8:
        return "نوسان گسترده — بدون الگوی فشرده"
    return "بدون الگوی کلاسیک واضح"


def _candle_pattern(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return "—"
    cur, prev = df.iloc[-1], df.iloc[-2]
    o, h, l, c = float(cur["Open"]), float(cur["High"]), float(cur["Low"]), float(cur["Close"])
    po, ph, pl, pc = float(prev["Open"]), float(prev["High"]), float(prev["Low"]), float(prev["Close"])
    body = abs(c - o)
    rng = h - l
    if rng == 0:
        return "—"
    upper = h - max(o, c)
    lower = min(o, c) - l

    if body / rng < 0.12:
        return "Doji — بلاتکلیفی"
    if lower > body * 2 and upper < body * 0.6:
        return "Hammer (چکش) — احتمال برگشت صعودی"
    if upper > body * 2 and lower < body * 0.6:
        return "Shooting Star — احتمال برگشت نزولی"
    if c > o and pc < po and c > po and o < pc:
        return "Bullish Engulfing — صعودی"
    if c < o and pc > po and c < po and o > pc:
        return "Bearish Engulfing — نزولی"
    if c > o:
        return "کندل صعودی ساده"
    return "کندل نزولی ساده"


def _volume_note(df: pd.DataFrame) -> str:
    vol = df["Volume"]
    avg = float(vol.tail(20).mean())
    last = float(vol.iloc[-1])
    ratio = last / avg if avg else 1
    if ratio >= 2:
        return f"حجم {ratio:.1f}x میانگین — مشارکت بالا، حرکت معتبرتر"
    if ratio < 0.7:
        return f"حجم {ratio:.1f}x میانگین — مشارکت ضعیف"
    return f"حجم {ratio:.1f}x میانگین — نرمال"


def _indicators_block(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    close = df["Close"]
    c = float(close.iloc[-1])
    rows: list[tuple[str, str, str]] = []

    r = float(rsi(close).iloc[-1])
    if r >= 70:
        rs = "اشباع خرید"
    elif r <= 30:
        rs = "اشباع فروش"
    else:
        rs = "خنثی"
    rows.append(("RSI (14)", f"{r:.1f}", rs))

    mline, msig, mhist = macd(close)
    mh = float(mhist.iloc[-1])
    rows.append(("MACD Hist", f"{mh:+.1f}", "مثبت" if mh > 0 else "منفی"))

    e20 = float(ema(close, 20).iloc[-1])
    e50 = float(ema(close, 50).iloc[-1])
    rows.append(("EMA 20/50", f"${e20:,.0f} / ${e50:,.0f}", "بالای EMA" if c > e20 else "زیر EMA"))

    s20 = float(sma(close, 20).iloc[-1])
    s50 = float(sma(close, 50).iloc[-1])
    rows.append(("SMA 20/50", f"${s20:,.0f} / ${s50:,.0f}", "—"))

    vw = float(vwap(df).iloc[-1])
    rows.append(("VWAP", f"${vw:,.0f}", "بالای VWAP" if c > vw else "زیر VWAP"))

    mid, upper, lower = bollinger_bands(close)
    bu, bl, bm = float(upper.iloc[-1]), float(lower.iloc[-1]), float(mid.iloc[-1])
    if c >= bu * 0.998:
        bs = "نزدیک باند بالا"
    elif c <= bl * 1.002:
        bs = "نزدیک باند پایین"
    else:
        bs = "داخل باند"
    rows.append(("Bollinger", f"${bl:,.0f}–${bu:,.0f}", bs))

    av = float(atr(df).iloc[-1])
    rows.append(("ATR (14)", f"${av:,.0f}", f"نوسان ~{av/c*100:.1f}%"))

    adx_val, pdi, mdi = adx(df)
    a = float(adx_val.iloc[-1])
    rows.append(("ADX", f"{a:.1f}", "روند قوی" if a >= 25 else "روند ضعیف"))

    sk, sd = stochastic_rsi(close)
    skv = float(sk.iloc[-1]) if not pd.isna(sk.iloc[-1]) else 50
    rows.append(("Stoch RSI", f"{skv:.0f}", "اشباع خرید" if skv > 80 else ("اشباع فروش" if skv < 20 else "خنثی")))

    _, st_dir = supertrend(df)
    std = int(st_dir.iloc[-1])
    rows.append(("SuperTrend", "صعودی" if std > 0 else "نزولی", "هم‌جهت روند" if std > 0 else "فشار نزولی"))

    ichi = ichimoku(df)
    tk = float(ichi["tenkan"].iloc[-1])
    kj = float(ichi["kijun"].iloc[-1])
    sa = float(ichi["senkou_a"].iloc[-1]) if not pd.isna(ichi["senkou_a"].iloc[-1]) else c
    sb = float(ichi["senkou_b"].iloc[-1]) if not pd.isna(ichi["senkou_b"].iloc[-1]) else c
    cloud = "بالای ابر" if c > max(sa, sb) else ("زیر ابر" if c < min(sa, sb) else "داخل ابر")
    rows.append(("Ichimoku", f"T={tk:,.0f} K={kj:,.0f}", cloud))

    ps = float(parabolic_sar(df).iloc[-1])
    rows.append(("Parabolic SAR", f"${ps:,.0f}", "صعودی" if c > ps else "نزولی"))

    return rows


def _build_summary(tfs: list[TimeframeTA], c: float, sup: float, res: float) -> str:
    daily = next((t for t in tfs if t.key == "1d"), tfs[0])
    h4 = next((t for t in tfs if t.key == "4h"), tfs[-1])
    parts = [
        f"جهت غالب: {daily.trend} (روزانه) و {h4.trend} (۴H).",
        f"قیمت بین حمایت ${sup:,.0f} و مقاومت ${res:,.0f}.",
    ]
    if "صعودی" in daily.trend and "صعودی" in h4.trend:
        parts.append("هم‌راستایی صعودی — لانگ با تأیید یا پولبک منطقی‌تر.")
    elif "نزولی" in daily.trend and "نزولی" in h4.trend:
        parts.append("هم‌راستایی نزولی — شورت یا صبر؛ لانگ پرریسک.")
    else:
        parts.append("تایم‌فریم‌ها هم‌جهت نیستند — صبر برای شکست.")
    return " ".join(parts)


def build_technical_report() -> TechnicalReport:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dfs: dict[str, pd.DataFrame] = {}
    for tf in TA_TIMEFRAMES:
        dfs[tf] = _closed(fetch_ohlcv(tf))

    primary = dfs["1h"]
    price = float(primary["Close"].iloc[-1])

    tfs: list[TimeframeTA] = []
    for tf in TA_TIMEFRAMES:
        df = dfs[tf]
        trend, note = _trend_from_df(df)
        adx_val, _, _ = adx(df)
        a = float(adx_val.iloc[-1]) if not pd.isna(adx_val.iloc[-1]) else 0
        tfs.append(
            TimeframeTA(
                key=tf,
                label=TIMEFRAME_LABELS[tf],
                price=float(df["Close"].iloc[-1]),
                trend=trend,
                trend_note=note,
                adx_val=a,
                structure=_market_structure(df),
            )
        )

    ref = dfs["4h"]
    supports, resistances = find_key_levels(ref)
    sup, res = nearest_support_resistance(price, supports, resistances)

    return TechnicalReport(
        generated_at=now,
        price=price,
        timeframes=tfs,
        supports=supports[-3:],
        resistances=resistances[-3:],
        nearest_support=sup,
        nearest_resistance=res,
        price_action=_market_structure(ref),
        classic_pattern=_classic_pattern(ref),
        candle_pattern=_candle_pattern(primary),
        candle_tf="۱H",
        volume_note=_volume_note(primary),
        indicators=_indicators_block(primary),
        summary=_build_summary(tfs, price, sup, res),
    )
