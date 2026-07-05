"""Macro economic calendar."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def get_upcoming_events(hours_ahead: int = 48) -> list[dict]:
    try:
        events = requests.get(CALENDAR_URL, timeout=15).json()
    except Exception:
        logger.warning("Calendar unavailable")
        return []

    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours_ahead)
    out: list[dict] = []
    for e in events:
        country = str(e.get("country", ""))
        impact = str(e.get("impact", ""))
        if country not in ("USD", "EUR") or impact not in ("High", "Medium"):
            continue
        try:
            t = datetime.fromisoformat(str(e.get("date", "")))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            else:
                t = t.astimezone(timezone.utc)
        except Exception:
            continue
        if now <= t <= end:
            out.append(
                {
                    "title": str(e.get("title", "")),
                    "country": country,
                    "impact": impact,
                    "time": t.strftime("%Y-%m-%d %H:%M UTC"),
                }
            )
    return sorted(out, key=lambda x: x["time"])[:8]
