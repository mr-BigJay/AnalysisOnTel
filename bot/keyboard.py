"""Telegram reply keyboard menu."""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

BTN_REPORT = "📊 گزارش"
BTN_STATUS = "📡 وضعیت"
BTN_STATS = "📈 آمار"
BTN_REVIEW = "📋 بازبینی"
BTN_BACKTEST = "📉 بکتست"
BTN_HELP = "❓ راهنما"

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_REPORT), KeyboardButton(BTN_STATUS)],
        [KeyboardButton(BTN_STATS), KeyboardButton(BTN_REVIEW)],
        [KeyboardButton(BTN_BACKTEST), KeyboardButton(BTN_HELP)],
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="یک گزینه از منو انتخاب کنید...",
)

MENU_ACTIONS = {
    BTN_REPORT: "report",
    "گزارش": "report",
    BTN_STATUS: "status",
    "وضعیت": "status",
    BTN_STATS: "stats",
    BTN_REVIEW: "review",
    BTN_BACKTEST: "backtest",
    BTN_HELP: "help",
}
