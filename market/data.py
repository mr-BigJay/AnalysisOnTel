"""Fetch OHLCV from Kraken public API."""

from __future__ import annotations

import pandas as pd
import requests

from config import KRAKEN_PAIR, TIMEFRAMES

KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"


def fetch_ohlcv(timeframe: str) -> pd.DataFrame:
    """Return OHLCV DataFrame indexed by UTC datetime."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    meta = TIMEFRAMES[timeframe]
    params = {"pair": KRAKEN_PAIR, "interval": meta["kraken"]}
    response = requests.get(KRAKEN_OHLC_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"Kraken API error: {payload['error']}")

    pair_key = next(iter(payload["result"]))
    rows = payload["result"][pair_key][-meta["candles"] :]

    df = pd.DataFrame(
        rows,
        columns=["time", "Open", "High", "Low", "Close", "vwap", "Volume", "count"],
    )
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = df[col].astype(float)
    return df[["Open", "High", "Low", "Close", "Volume"]]
