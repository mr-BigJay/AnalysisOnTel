"""High-impact economic event risk filter."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
HIGH_IMPACT = {"High", "Medium"}
WATCH_COUNTRIES = {"USD", "EUR"}


def get_event_risk(hours_ahead: int = 4) -> tuple[bool, str | None]:
    """
    Return (is_risky, description).
    Blocks new entry signals around major USD/EUR events.
    """
    try:
        resp = requests.get(CALENDAR_URL, timeout=15)
        resp.raise_for_status()
        events = resp.json()
    except Exception:
        logger.warning("Event calendar unavailable")
        return False, None

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=hours_ahead)

    risky: list[str] = []
    for event in events:
        title = str(event.get("title", ""))
        country = str(event.get("country", ""))
        impact = str(event.get("impact", ""))
        if country not in WATCH_COUNTRIES or impact not in HIGH_IMPACT:
            continue
        try:
            # ISO format with timezone offset
            raw = str(event.get("date", ""))
            event_time = datetime.fromisoformat(raw)
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            else:
                event_time = event_time.astimezone(timezone.utc)
        except Exception:
            continue
        if now <= event_time <= window_end:
            risky.append(f"{title} ({country}, {impact})")

    if not risky:
        return False, None

    note = " | ".join(risky[:3])
    if len(risky) > 3:
        note += f" +{len(risky) - 3} more"
    return True, note
