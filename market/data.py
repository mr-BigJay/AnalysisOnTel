"""Fetch OHLCV from Kraken public API."""

from __future__ import annotations

import pandas as pd
import requests

from config import KRAKEN_PAIR, TIMEFRAMES

KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"


def fetch_ohlcv(timeframe: str, candles: int | None = None) -> pd.DataFrame:
    meta = TIMEFRAMES.get(timeframe)
    if not meta:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    limit = candles or meta["candles"]
    response = requests.get(
        KRAKEN_OHLC_URL,
        params={"pair": KRAKEN_PAIR, "interval": meta["kraken"]},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"Kraken API error: {payload['error']}")

    pair_key = next(iter(payload["result"]))
    rows = payload["result"][pair_key][-limit:]
    df = pd.DataFrame(
        rows,
        columns=["time", "Open", "High", "Low", "Close", "vwap", "Volume", "count"],
    )
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = df[col].astype(float)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def closed_candles(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1] if len(df) > 1 else df
