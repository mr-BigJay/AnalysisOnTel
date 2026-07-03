"""Generate BTC chart image for Telegram."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR
from market.data import fetch_ohlcv
from market.indicators import ema
from market.levels import find_key_levels, nearest_support_resistance


def generate_chart(timeframe: str = "4h", output_path: Path | None = None) -> Path:
    df = fetch_ohlcv(timeframe, candles=80)
    close = df["Close"]
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    price = float(close.iloc[-1])
    supports, resistances = find_key_levels(df)
    support, resistance = nearest_support_resistance(price, supports, resistances)

    apds = [
        mpf.make_addplot(ema20, color="#f59e0b", width=1.0),
        mpf.make_addplot(ema50, color="#3b82f6", width=1.0),
    ]

    style = mpf.make_mpf_style(base_mpf_style="nightclouds")
    out = output_path or (OUTPUT_DIR / "btc_chart.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        addplot=apds,
        volume=True,
        figsize=(10, 6),
        returnfig=True,
        title=f"BTC/USD {timeframe.upper()} | ${price:,.0f}",
        tight_layout=True,
    )
    ax = axes[0]
    ax.axhline(support, color="#22c55e", linestyle="--", alpha=0.8)
    ax.axhline(resistance, color="#ef4444", linestyle="--", alpha=0.8)
    fig.set_size_inches(10, 6)
    fig.savefig(out, dpi=120, pad_inches=0.2)
    plt.close(fig)
    return out
