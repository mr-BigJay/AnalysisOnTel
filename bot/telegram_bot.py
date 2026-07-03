"""Telegram bot for AnalysisOnTel market reports."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from backtest.report import run_and_format
from bot.keyboard import (
    BTN_BACKTEST,
    BTN_HELP,
    BTN_REPORT,
    BTN_REVIEW,
    BTN_STATS,
    BTN_STATUS,
    MENU_ACTIONS,
    MENU_KEYBOARD,
)
from chart.generator import generate_chart
from config import TELEGRAM_BOT_TOKEN
from market.status import fetch_market_status
from report.engine import generate_report_messages
from report.status_formatter import format_status_report
from tracking.review import format_review_report
from tracking.stats import format_stats_report

logger = logging.getLogger(__name__)


async def _reply_with_menu(update: Update, text: str, html: bool = False) -> None:
    kwargs = {"reply_markup": MENU_KEYBOARD}
    if html:
        await update.message.reply_html(text, **kwargs)
    else:
        await update.message.reply_text(text, **kwargs)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 <b>AnalysisOnTel</b>\n\n"
        "ربات تحلیل BTC — گزارش نهادی (روزانه + ۴H + ۱H)\n\n"
        "از <b>منوی پایین</b> یک گزینه را انتخاب کنید:\n\n"
        "📊 گزارش — تحلیل نهادی + SMC + چارت\n"
        "📡 وضعیت — روند ۵دقیقه / ۱۵دقیقه / ۱H / ۴H\n"
        "📈 آمار — Win Rate و خود-اصلاح\n"
        "📋 بازبینی — پیش‌بینی vs واقعیت\n"
        "📉 بکتست — تست تاریخی\n"
        "❓ راهنما — همین پیام\n\n"
        "قانون: روزانه جهت اصلی است.\n"
        "خلاف روند بلندمدت = پرریسک ⛔"
    )
    await update.message.reply_html(text, reply_markup=MENU_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ در حال دریافت داده و تحلیل...", reply_markup=MENU_KEYBOARD)

    try:
        _, messages = generate_report_messages(source="telegram_report")
        for i, text in enumerate(messages):
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=MENU_KEYBOARD if i == len(messages) - 1 else None,
            )

        try:
            chart_path = generate_chart("4h")
            with open(chart_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption="📈 چارت BTC — ۴H",
                    reply_markup=MENU_KEYBOARD,
                )
        except Exception:
            logger.exception("Chart generation failed")
    except Exception as exc:
        logger.exception("Report generation failed")
        await update.message.reply_text(f"❌ خطا در تولید گزارش: {exc}", reply_markup=MENU_KEYBOARD)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ در حال دریافت وضعیت...", reply_markup=MENU_KEYBOARD)
    try:
        status = fetch_market_status()
        text = format_status_report(status)
        await _reply_with_menu(update, text, html=True)
    except Exception as exc:
        logger.exception("Status failed")
        await update.message.reply_text(f"❌ خطا در وضعیت: {exc}", reply_markup=MENU_KEYBOARD)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = format_stats_report()
        await _reply_with_menu(update, text, html=True)
    except Exception as exc:
        logger.exception("Stats failed")
        await update.message.reply_text(f"❌ خطا در آمار: {exc}", reply_markup=MENU_KEYBOARD)


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = format_review_report()
        await _reply_with_menu(update, text, html=True)
    except Exception as exc:
        logger.exception("Review failed")
        await update.message.reply_text(f"❌ خطا در بازبینی: {exc}", reply_markup=MENU_KEYBOARD)


async def backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⏳ بکتست در حال اجرا (۳۰–۶۰ ثانیه)...", reply_markup=MENU_KEYBOARD
    )
    try:
        text = run_and_format()
        await _reply_with_menu(update, text, html=True)
    except Exception as exc:
        logger.exception("Backtest failed")
        await update.message.reply_text(f"❌ خطا در بکتست: {exc}", reply_markup=MENU_KEYBOARD)


async def menu_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route reply-keyboard menu button presses."""
    text = (update.message.text or "").strip()
    action = MENU_ACTIONS.get(text)
    if action == "report":
        await report_command(update, context)
    elif action == "status":
        await status_command(update, context)
    elif action == "stats":
        await stats_command(update, context)
    elif action == "review":
        await review_command(update, context)
    elif action == "backtest":
        await backtest_command(update, context)
    elif action == "help":
        await help_command(update, context)


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
    app.add_handler(CommandHandler("gozaresh", report_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("vaziat", status_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("review", review_command))
    app.add_handler(CommandHandler("backtest", backtest_command))
    # Menu buttons (must be after commands; exclude commands starting with /)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu_text_handler),
    )
    return app


def run_bot() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    app = build_application()
    logger.info("Starting Telegram bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
