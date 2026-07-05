"""Telegram bot — BTC notifications only."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.keyboard import (
    BTN_BRIEFING,
    BTN_HELP,
    BTN_MARKET,
    BTN_STATUS,
    BTN_TECHNICAL,
    MENU_ACTIONS,
    MENU_KEYBOARD,
)
from bot.briefing_format import format_briefing_report
from bot.market_context_format import format_market_context_report
from bot.status_format import format_status_report
from bot.technical_format import format_technical_report
from config import TELEGRAM_BOT_TOKEN
from market.briefing import build_briefing_report
from market.context import fetch_market_context
from market.status import fetch_market_status
from market.technical import build_technical_report

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "👋 <b>AnalysisOnTel — BTC Alerts</b>\n\n"
    "ربات هشدار BTC (سطح ۱ تا ۳):\n\n"
    "<b>سطح ۱</b> — RSI، divergence، شکست سطح\n"
    "<b>سطح ۲</b> — Liquidity Grab، MSS، Retest\n"
    "<b>سطح ۳</b> — ماکرو، Funding، F&G، Volume\n\n"
    "📡 <b>وضعیت</b> — روند 1m/5m/15m/1H/4H\n"
    "🌐 <b>بازار</b> — Funding، Fear&Greed، L/S، OI، ماکرو\n"
    "📊 <b>تکنیکال</b> — تحلیل کامل TA (مجزا از هشدارها)\n"
    "📋 <b>گزارش</b> — گزارش جامع ۴ ساعته (اخبار + TA + ICT)\n\n"
    "حالت bot-scheduled: هشدارها + گزارش ۴H خودکار."
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


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ در حال دریافت داده بازار...", reply_markup=MENU_KEYBOARD)
    try:
        report = fetch_market_context()
        text = format_market_context_report(report)
        if len(text) > 4000:
            text = text[:3990] + "\n..."
        await update.message.reply_html(text, reply_markup=MENU_KEYBOARD)
    except Exception as exc:
        logger.exception("Market context failed")
        await update.message.reply_text(f"❌ خطا: {exc}", reply_markup=MENU_KEYBOARD)


async def technical_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "⏳ در حال تهیه تحلیل تکنیکال...", reply_markup=MENU_KEYBOARD
    )
    try:
        report = build_technical_report()
        messages = format_technical_report(report)
        for i, text in enumerate(messages):
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=MENU_KEYBOARD if i == len(messages) - 1 else None,
            )
    except Exception as exc:
        logger.exception("Technical analysis failed")
        await update.message.reply_text(f"❌ خطا: {exc}", reply_markup=MENU_KEYBOARD)


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "⏳ در حال تهیه گزارش ۴ ساعته...", reply_markup=MENU_KEYBOARD
    )
    try:
        report = build_briefing_report(persist=False)
        messages = format_briefing_report(report)
        for i, text in enumerate(messages):
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=MENU_KEYBOARD if i == len(messages) - 1 else None,
            )
    except Exception as exc:
        logger.exception("Briefing failed")
        await update.message.reply_text(f"❌ خطا: {exc}", reply_markup=MENU_KEYBOARD)


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    action = MENU_ACTIONS.get(text)
    if action == "status":
        await status_command(update, context)
    elif action == "market":
        await market_command(update, context)
    elif action == "technical":
        await technical_command(update, context)
    elif action == "briefing":
        await briefing_command(update, context)
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
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("bazar", market_command))
    app.add_handler(CommandHandler("technical", technical_command))
    app.add_handler(CommandHandler("teknikal", technical_command))
    app.add_handler(CommandHandler("briefing", briefing_command))
    app.add_handler(CommandHandler("gozaresh", briefing_command))
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
