#!/usr/bin/env python3
"""Generate BTC chart with support/resistance and indicator overlays."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import mplfinance as mpf
import numpy as np
import pandas as pd
import requests

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SYMBOL = "BTCUSDT"
INTERVAL = "4h"
LIMIT = 120


def fetch_ohlcv(symbol: str = SYMBOL, interval: str = INTERVAL, limit: int = LIMIT) -> pd.DataFrame:
    """Fetch OHLCV from Kraken (Binance may be geo-blocked in some regions)."""
    interval_map = {"1h": 60, "4h": 240, "1d": 1440}
    kraken_interval = interval_map.get(interval, 240)

    url = "https://api.kraken.com/0/public/OHLC"
    params = {"pair": "XBTUSD", "interval": kraken_interval}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"Kraken API error: {payload['error']}")

    pair_key = next(iter(payload["result"]))
    rows = payload["result"][pair_key][-limit:]

    df = pd.DataFrame(rows, columns=["time", "Open", "High", "Low", "Close", "vwap", "Volume", "count"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = df[col].astype(float)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def find_swing_levels(df: pd.DataFrame, window: int = 5) -> tuple[list[float], list[float]]:
    highs = df["High"].values
    lows = df["Low"].values
    resistance: list[float] = []
    support: list[float] = []

    for i in range(window, len(df) - window):
        local_high = highs[i - window : i + window + 1].max()
        local_low = lows[i - window : i + window + 1].min()
        if highs[i] == local_high:
            resistance.append(float(highs[i]))
        if lows[i] == local_low:
            support.append(float(lows[i]))

    def cluster(levels: list[float], tolerance: float = 0.008) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters: list[list[float]] = [[levels[0]]]
        for level in levels[1:]:
            if abs(level - clusters[-1][-1]) / clusters[-1][-1] <= tolerance:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [float(np.mean(cluster)) for cluster in clusters]

    return cluster(support)[-3:], cluster(resistance)[-3:]


def build_chart(df: pd.DataFrame, support: list[float], resistance: list[float], output_path: Path) -> dict:
    close = df["Close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    last_close = float(close.iloc[-1])

    apds = [
        mpf.make_addplot(ema20, color="#f59e0b", width=1.2),
        mpf.make_addplot(ema50, color="#3b82f6", width=1.2),
    ]

    mc = mpf.make_marketcolors(
        up="#22c55e",
        down="#ef4444",
        edge="inherit",
        wick="inherit",
        volume="in",
    )
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        gridstyle="--",
        gridcolor="#334155",
        facecolor="#0f172a",
        edgecolor="#0f172a",
        figcolor="#0f172a",
        rc={
            "axes.labelcolor": "#e2e8f0",
            "xtick.color": "#94a3b8",
            "ytick.color": "#94a3b8",
            "font.size": 10,
        },
    )

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        addplot=apds,
        volume=True,
        figsize=(14, 8),
        returnfig=True,
        title=f"BTC/USD — {INTERVAL.upper()} | Last: ${last_close:,.2f}",
        ylabel="Price (USD)",
        ylabel_lower="Volume",
        datetime_format="%m-%d %H:%M",
        tight_layout=True,
    )

    ax_price = axes[0]

    def label_level(level: float, text: str, color: str) -> None:
        ax_price.axhline(level, color=color, linestyle="--", linewidth=1.0, alpha=0.75)
        ax_price.text(
            0.99,
            level,
            text,
            transform=ax_price.get_yaxis_transform(),
            color=color,
            va="center",
            ha="right",
            fontsize=9,
            fontweight="bold",
            clip_on=False,
        )

    for level in support:
        label_level(level, f"Support ${level:,.0f}", "#22c55e")

    for level in resistance:
        label_level(level, f"Resistance ${level:,.0f}", "#ef4444")

    entry_low = float(ema20.iloc[-1] * 0.998)
    entry_high = float(ema20.iloc[-1] * 1.002)
    stop_loss = min(support) * 0.995 if support else float(close.iloc[-20:].min())
    tp1 = max(resistance) if resistance else float(close.iloc[-1] * 1.03)

    ax_price.axhspan(entry_low, entry_high, color="#3b82f6", alpha=0.15)
    ax_price.text(
        0.55,
        (entry_low + entry_high) / 2,
        "Long Entry Zone",
        transform=ax_price.get_yaxis_transform(),
        color="#93c5fd",
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#1e3a5f", edgecolor="#3b82f6", alpha=0.9),
    )

    ax_price.axhline(stop_loss, color="#f97316", linestyle=":", linewidth=1.2, alpha=0.9)
    ax_price.text(
        0.08,
        stop_loss,
        f"Stop Loss ${stop_loss:,.0f}",
        transform=ax_price.get_yaxis_transform(),
        color="#fdba74",
        fontsize=9,
    )

    ax_price.axhline(tp1, color="#a855f7", linestyle=":", linewidth=1.2, alpha=0.9)
    ax_price.text(
        0.35,
        tp1,
        f"Take Profit ${tp1:,.0f}",
        transform=ax_price.get_yaxis_transform(),
        color="#d8b4fe",
        fontsize=9,
    )

    legend_handles = [
        mpatches.Patch(color="#f59e0b", label="EMA 20"),
        mpatches.Patch(color="#3b82f6", label="EMA 50"),
        mpatches.Patch(color="#22c55e", label="Support"),
        mpatches.Patch(color="#ef4444", label="Resistance"),
        mpatches.Patch(color="#3b82f6", alpha=0.3, label="Entry Zone"),
        mpatches.Patch(color="#f97316", label="Stop Loss"),
        mpatches.Patch(color="#a855f7", label="Take Profit"),
    ]
    ax_price.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.85)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.text(
        0.01,
        0.01,
        f"AnalysisOnTel | Kraken BTC/USD | Generated: {timestamp}",
        color="#64748b",
        fontsize=8,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.set_size_inches(14, 8)
    fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor(), pad_inches=0.25)
    plt.close(fig)

    return {
        "last_close": last_close,
        "ema20": float(ema20.iloc[-1]),
        "ema50": float(ema50.iloc[-1]),
        "support": support,
        "resistance": resistance,
        "entry_zone": [entry_low, entry_high],
        "stop_loss": stop_loss,
        "take_profit": tp1,
        "output_path": str(output_path),
    }


def main() -> None:
    df = fetch_ohlcv()
    support, resistance = find_swing_levels(df)
    output_path = OUTPUT_DIR / "btc_chart.png"
    meta = build_chart(df, support, resistance, output_path)
    meta_path = OUTPUT_DIR / "btc_chart_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
