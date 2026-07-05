"""Application configuration — BTC notification bot."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

KRAKEN_PAIR = "XBTUSD"
SYMBOL = "BTC/USD"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [
    cid.strip()
    for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if cid.strip()
]

# Kraken OHLC intervals
TIMEFRAME_LABELS = {
    "1m": "۱ دقیقه",
    "5m": "۵ دقیقه",
    "15m": "۱۵ دقیقه",
    "1h": "۱ ساعته",
    "4h": "۴ ساعته",
    "1d": "روزانه",
}

TIMEFRAMES = {
    "1m": {"label": "۱ دقیقه", "kraken": 1, "candles": 120},
    "5m": {"label": "۵ دقیقه", "kraken": 5, "candles": 120},
    "15m": {"label": "۱۵ دقیقه", "kraken": 15, "candles": 96},
    "1h": {"label": "۱ ساعته", "kraken": 60, "candles": 120},
    "4h": {"label": "۴ ساعته", "kraken": 240, "candles": 120},
    "1d": {"label": "روزانه", "kraken": 1440, "candles": 120},
}

TA_TIMEFRAMES = ["1d", "4h", "1h"]

# Which TFs to scan per signal type
RSI_ALERT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]
LEVEL_BREAK_TIMEFRAMES = ["1h", "4h"]
SMC_TIMEFRAMES = ["15m", "1h"]
STATUS_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]

RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))

FNG_EXTREME_FEAR = int(os.getenv("FNG_EXTREME_FEAR", "25"))
FNG_EXTREME_GREED = int(os.getenv("FNG_EXTREME_GREED", "75"))
FUNDING_EXTREME = float(os.getenv("FUNDING_EXTREME", "0.0003"))
VOLUME_SPIKE_RATIO = float(os.getenv("VOLUME_SPIKE_RATIO", "2.0"))

REPORT_INTERVAL_HOURS = int(os.getenv("REPORT_INTERVAL_HOURS", "4"))
REPORT_ENABLED = os.getenv("REPORT_ENABLED", "true").lower() in ("1", "true", "yes")
# UTC hours when 4H briefing runs (5 min after candle close)
REPORT_CRON_HOURS = os.getenv("REPORT_CRON_HOURS", "0,4,8,12,16,20")
