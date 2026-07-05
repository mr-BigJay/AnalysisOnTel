"""AnalysisOnTel — institutional BTC web dashboard."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_PATH = DATA_DIR / "latest_report.json"
HISTORY_PATH = DATA_DIR / "report_history.json"

KRAKEN_PAIR = "XBTUSD"
SYMBOL = "BTC/USD"

WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "")  # empty = no auth

REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "240"))

TIMEFRAMES = {
    "15m": {"label": "15m", "kraken": 15, "candles": 200},
    "1h": {"label": "1H", "kraken": 60, "candles": 200},
    "4h": {"label": "4H", "kraken": 240, "candles": 200},
    "1d": {"label": "1D", "kraken": 1440, "candles": 120},
    "1w": {"label": "1W", "kraken": 10080, "candles": 52},
}

ANALYSIS_TIMEFRAMES = ["1w", "1d", "4h", "1h", "15m"]
PRIMARY_TF = "4h"
ENTRY_TF = "1h"

MAX_RISK_PCT = float(os.getenv("MAX_RISK_PCT", "1.0"))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "20"))
