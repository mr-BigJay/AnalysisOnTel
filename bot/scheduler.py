"""Scheduled candle-close alerts."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, TIMEFRAMES
from report.engine import generate_candle_alert
from tracking.evaluator import evaluate_pending
from tracking.tuning import auto_tune

logger = logging.getLogger(__name__)

_last_candle: dict[str, int] = {}


def _get_latest_candle_ts(timeframe: str) -> int:
    from market.data import fetch_ohlcv

    df = fetch_ohlcv(timeframe)
    return int(df.index[-1].timestamp())


async def _send_alerts(text: str) -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for chat_id in TELEGRAM_CHAT_IDS:
        await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="HTML")


def _check_and_alert(timeframe: str) -> None:
    if not TELEGRAM_CHAT_IDS or not TELEGRAM_BOT_TOKEN:
        return

    try:
        latest = _get_latest_candle_ts(timeframe)
        if _last_candle.get(timeframe) == latest:
            return
        _last_candle[timeframe] = latest

        text = generate_candle_alert(timeframe)
        asyncio.run(_send_alerts(text))
        logger.info("Candle alert sent for %s at %s", timeframe, datetime.now(timezone.utc))
    except Exception:
        logger.exception("Candle alert failed for %s", timeframe)


def _run_outcome_evaluation() -> None:
    try:
        n = evaluate_pending()
        if n:
            logger.info("Evaluated %s pending predictions", n)
        tuned = auto_tune()
        if tuned and tuned.last_tune_reason and TELEGRAM_CHAT_IDS and TELEGRAM_BOT_TOKEN:
            text = (
                "🔧 <b>خود-اصلاح ربات</b>\n\n"
                f"{tuned.last_tune_reason}\n\n"
                f"حد ورود: {tuned.min_entry_score}\n"
                f"حد چک‌لیست: {tuned.min_checklist_score}\n"
                f"حداقل ✅: {tuned.min_checklist_passed}/10"
            )
            asyncio.run(_send_alerts(text))
    except Exception:
        logger.exception("Outcome evaluation failed")


def _run_weekly_backtest() -> None:
    try:
        from backtest.report import run_and_format

        text = run_and_format()
        if TELEGRAM_CHAT_IDS and TELEGRAM_BOT_TOKEN:
            asyncio.run(_send_alerts("📅 <b>بکتست هفتگی</b>\n\n" + text))
        logger.info("Weekly backtest completed")
    except Exception:
        logger.exception("Weekly backtest failed")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")

    # Check every minute if a new candle closed
    for tf in TIMEFRAMES:
        scheduler.add_job(
            _check_and_alert,
            "interval",
            minutes=1,
            args=[tf],
            id=f"candle_{tf}",
            replace_existing=True,
        )

    scheduler.add_job(
        _run_outcome_evaluation,
        "interval",
        minutes=15,
        id="outcome_eval",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_weekly_backtest,
        "cron",
        day_of_week="sun",
        hour=6,
        minute=0,
        id="weekly_backtest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Candle-close scheduler started for: %s", list(TIMEFRAMES.keys()))
    return scheduler
