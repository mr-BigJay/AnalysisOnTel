"""Technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI (matches TradingView / industry default)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = ema(series, 12)
    slow = ema(series, 26)
    line = fast - slow
    signal = ema(line, 9)
    hist = line - signal
    return line, signal, hist


def macd_histogram(series: pd.Series) -> pd.Series:
    return macd(series)[2]


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
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
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return middle, upper, lower


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df["Volume"].replace(0, pd.NA)
    return (tp * df["Volume"]).cumsum() / vol.cumsum()


def adx(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = atr(df, period)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(span=period, adjust=False).mean() / tr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(span=period, adjust=False).mean() / tr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)) * 100
    adx_line = dx.ewm(span=period, adjust=False).mean()
    return adx_line, plus_di, minus_di


def stochastic_rsi(
    series: pd.Series, rsi_period: int = 14, stoch_period: int = 14, smooth_k: int = 3, smooth_d: int = 3
) -> tuple[pd.Series, pd.Series]:
    r = rsi(series, rsi_period)
    min_r = r.rolling(stoch_period).min()
    max_r = r.rolling(stoch_period).max()
    stoch = ((r - min_r) / (max_r - min_r).replace(0, pd.NA)) * 100
    k = stoch.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    hl2 = (df["High"] + df["Low"]) / 2
    atr_val = atr(df, period)
    basic_ub = hl2 + multiplier * atr_val
    basic_lb = hl2 - multiplier * atr_val

    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()
    for i in range(1, len(df)):
        if basic_ub.iloc[i] < final_ub.iloc[i - 1] or df["Close"].iloc[i - 1] > final_ub.iloc[i - 1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i - 1]
        if basic_lb.iloc[i] > final_lb.iloc[i - 1] or df["Close"].iloc[i - 1] < final_lb.iloc[i - 1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i - 1]

    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    for i in range(len(df)):
        if i == 0:
            st.iloc[i] = final_ub.iloc[i]
            direction.iloc[i] = -1
            continue
        prev_st = st.iloc[i - 1]
        if prev_st == final_ub.iloc[i - 1]:
            if df["Close"].iloc[i] <= final_ub.iloc[i]:
                st.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
            else:
                st.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
        else:
            if df["Close"].iloc[i] >= final_lb.iloc[i]:
                st.iloc[i] = final_lb.iloc[i]
                direction.iloc[i] = 1
            else:
                st.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
    return st, direction


def ichimoku(df: pd.DataFrame) -> dict[str, pd.Series]:
    tenkan = (df["High"].rolling(9).max() + df["Low"].rolling(9).min()) / 2
    kijun = (df["High"].rolling(26).max() + df["Low"].rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((df["High"].rolling(52).max() + df["Low"].rolling(52).min()) / 2).shift(26)
    return {"tenkan": tenkan, "kijun": kijun, "senkou_a": senkou_a, "senkou_b": senkou_b}


def parabolic_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    high = df["High"].values
    low = df["Low"].values
    length = len(df)
    psar = np.zeros(length)
    bull = True
    af = af_step
    ep = low[0]
    psar[0] = high[0]

    for i in range(1, length):
        prev = psar[i - 1]
        if bull:
            psar[i] = prev + af * (ep - prev)
            psar[i] = min(psar[i], low[i - 1], low[i - 2] if i > 1 else low[i - 1])
            if low[i] < psar[i]:
                bull = False
                psar[i] = ep
                ep = low[i]
                af = af_step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            psar[i] = prev + af * (ep - prev)
            psar[i] = max(psar[i], high[i - 1], high[i - 2] if i > 1 else high[i - 1])
            if high[i] > psar[i]:
                bull = True
                psar[i] = ep
                ep = high[i]
                af = af_step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

    return pd.Series(psar, index=df.index)


def kdj(
    df: pd.DataFrame, period: int = 9, smooth_k: int = 3, smooth_d: int = 3
) -> tuple[pd.Series, pd.Series, pd.Series]:
    low_min = df["Low"].rolling(period).min()
    high_max = df["High"].rolling(period).max()
    span = (high_max - low_min).replace(0, pd.NA)
    rsv = ((df["Close"] - low_min) / span * 100).fillna(50)
    k = rsv.ewm(alpha=1 / smooth_k, adjust=False).mean()
    d = k.ewm(alpha=1 / smooth_d, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j
