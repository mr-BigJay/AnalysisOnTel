"""Technical indicators."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd_histogram(series: pd.Series) -> pd.Series:
    fast = ema(series, 12)
    slow = ema(series, 26)
    macd_line = fast - slow
    signal = ema(macd_line, 9)
    return macd_line - signal


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (middle, upper, lower) Bollinger Bands."""
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return middle, upper, lower


def kdj(
    df: pd.DataFrame, period: int = 9, smooth_k: int = 3, smooth_d: int = 3
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (K, D, J) stochastic-style KDJ."""
    low_min = df["Low"].rolling(period).min()
    high_max = df["High"].rolling(period).max()
    span = (high_max - low_min).replace(0, pd.NA)
    rsv = ((df["Close"] - low_min) / span * 100).fillna(50)
    k = rsv.ewm(alpha=1 / smooth_k, adjust=False).mean()
    d = k.ewm(alpha=1 / smooth_d, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j
