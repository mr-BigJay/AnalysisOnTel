"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
PREDICTIONS_DB = DATA_DIR / "predictions.db"

# Kraken pair for BTC/USD
KRAKEN_PAIR = "XBTUSD"

# Telegram — set TELEGRAM_BOT_TOKEN in environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Comma-separated chat IDs allowed to receive scheduled alerts (optional)
TELEGRAM_CHAT_IDS = [
    cid.strip()
    for cid in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if cid.strip()
]

# Timeframes used for analysis
TIMEFRAMES = {
    "1d": {"label": "روزانه", "kraken": 1440, "candles": 120},
    "4h": {"label": "۴ ساعته", "kraken": 240, "candles": 120},
    "1h": {"label": "۱ ساعته", "kraken": 60, "candles": 120},
}

# Minimum quality score (0-100) to recommend entry
MIN_ENTRY_SCORE = 70

# Hours after a prediction before outcome evaluation (matches 4H candle)
PREDICTION_EVAL_HOURS = int(os.getenv("PREDICTION_EVAL_HOURS", "4"))

# Minimum minutes between duplicate logs for same bias/action
PREDICTION_LOG_COOLDOWN_MIN = int(os.getenv("PREDICTION_LOG_COOLDOWN_MIN", "60"))
