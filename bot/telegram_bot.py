"""Telegram bot — BTC notifications only."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.keyboard import BTN_HELP, BTN_STATUS, MENU_ACTIONS, MENU_KEYBOARD
from bot.status_format import format_status_report
from config import TELEGRAM_BOT_TOKEN
from market.status import fetch_market_status

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "👋 <b>AnalysisOnTel — BTC Alerts</b>\n\n"
    "ربات هشدار BTC (سطح ۱ تا ۳):\n\n"
    "<b>سطح ۱</b>\n"
    "• RSI oversold / overbought\n"
    "• RSI divergence\n"
    "• شکست سطح (1H / 4H)\n\n"
    "<b>سطح ۲</b>\n"
    "• Liquidity Grab\n"
    "• MSS\n"
    "• Breakout + Retest\n\n"
    "<b>سطح ۳</b>\n"
    "• رویداد ماکرو\n"
    "• Fear & Greed افراطی\n"
    "• Funding افراطی\n"
    "• Volume spike\n\n"
    "📡 <b>وضعیت</b> — روند 1m/5m/15m/1H/4H\n\n"
    "حالت bot-scheduled: هشدارها خودکار ارسال می‌شوند."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(HELP_TEXT, reply_markup=MENU_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ ...", reply_markup=MENU_KEYBOARD)
    try:
        status = fetch_market_status()
        await update.message.reply_html(
            format_status_report(status), reply_markup=MENU_KEYBOARD
        )
    except Exception as exc:
        logger.exception("Status failed")
        await update.message.reply_text(f"❌ خطا: {exc}", reply_markup=MENU_KEYBOARD)


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    action = MENU_ACTIONS.get(text)
    if action == "status":
        await status_command(update, context)
    elif action == "help":
        await help_command(update, context)


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("vaziat", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    return app


def run_bot() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    app = build_application()
    logger.info("Starting BTC notification bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
