"""Scheduled BTC notification scanner."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import (
    REPORT_CRON_HOURS,
    REPORT_ENABLED,
    SCAN_INTERVAL_MINUTES,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_IDS,
)
from market.briefing import run_scheduled_briefing
from notifications.engine import run_btc_notifications

logger = logging.getLogger(__name__)


async def _send_all(texts: list[str]) -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for chat_id in TELEGRAM_CHAT_IDS:
        for text in texts:
            await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML")


def _scan() -> None:
    if not TELEGRAM_CHAT_IDS or not TELEGRAM_BOT_TOKEN:
        return
    try:
        alerts = run_btc_notifications()
        if alerts:
            asyncio.run(_send_all(alerts))
            logger.info("Sent %s BTC alerts at %s", len(alerts), datetime.now(timezone.utc))
    except Exception:
        logger.exception("Notification scan failed")


def _briefing() -> None:
    if not REPORT_ENABLED or not TELEGRAM_CHAT_IDS or not TELEGRAM_BOT_TOKEN:
        return
    try:
        messages = run_scheduled_briefing()
        if messages:
            asyncio.run(_send_all(messages))
            logger.info("Sent 4H briefing (%s parts) at %s", len(messages), datetime.now(timezone.utc))
    except Exception:
        logger.exception("4H briefing failed")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _scan,
        "interval",
        minutes=SCAN_INTERVAL_MINUTES,
        id="btc_scan",
        replace_existing=True,
    )
    if REPORT_ENABLED:
        hours = REPORT_CRON_HOURS.strip()
        scheduler.add_job(
            _briefing,
            CronTrigger(minute=5, hour=hours, timezone="UTC"),
            id="btc_briefing_4h",
            replace_existing=True,
        )
        logger.info("4H briefing scheduled at minute 5, hours %s UTC", hours)
    scheduler.start()
    logger.info("BTC notification scheduler every %s min", SCAN_INTERVAL_MINUTES)
    return scheduler
