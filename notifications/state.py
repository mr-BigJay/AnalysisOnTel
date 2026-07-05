"""Unified notification state persistence."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)

STATE_PATH = DATA_DIR / "notifications_state.json"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to load notification state")
        return {}


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def already_sent(state: dict, key: str, fingerprint: str) -> bool:
    return state.get(key, {}).get("fingerprint") == fingerprint


def mark_sent(state: dict, key: str, fingerprint: str, extra: dict | None = None) -> None:
    payload = {"fingerprint": fingerprint, **(extra or {})}
    state[key] = payload
