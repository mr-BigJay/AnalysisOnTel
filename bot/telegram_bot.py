"""Telegram bot for AnalysisOnTel market reports."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from report.engine import generate_report

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 <b>AnalysisOnTel</b>\n\n"
        "ربات گزارش بازار BTC — روزانه + ۴H + ۱H\n\n"
        "دستورات:\n"
        "/report — گزارش کامل لحظه‌ای\n"
        "/گزارش — همان گزارش (فارسی)\n"
        "/help — راهنما\n\n"
        "قانون: جهت روزانه تعیین‌کننده است.\n"
        "خلاف روند بلندمدت = پرریسک ⛔"
    )
    await update.message.reply_html(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ در حال دریافت داده و تحلیل...")

    try:
        _, text = generate_report()
        # Telegram message limit is 4096 chars
        if len(text) > 4000:
            text = text[:3990] + "\n..."
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as exc:
        logger.exception("Report generation failed")
        await update.message.reply_text(f"❌ خطا در تولید گزارش: {exc}")


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Create a bot via @BotFather and export the token."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("گزارش", report_command))
    return app


def run_bot() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    app = build_application()
    logger.info("Starting Telegram bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
