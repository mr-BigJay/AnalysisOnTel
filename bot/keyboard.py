"""Telegram reply keyboard."""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

BTN_STATUS = "📡 وضعیت"
BTN_MARKET = "🌐 بازار"
BTN_TECHNICAL = "📊 تکنیکال"
BTN_BRIEFING = "📋 گزارش"
BTN_HELP = "❓ راهنما"

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_STATUS), KeyboardButton(BTN_MARKET)],
        [KeyboardButton(BTN_TECHNICAL), KeyboardButton(BTN_BRIEFING)],
        [KeyboardButton(BTN_HELP)],
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="یک گزینه انتخاب کنید...",
)

MENU_ACTIONS = {
    BTN_STATUS: "status",
    "وضعیت": "status",
    BTN_MARKET: "market",
    "بازار": "market",
    BTN_TECHNICAL: "technical",
    "تکنیکال": "technical",
    BTN_BRIEFING: "briefing",
    "گزارش": "briefing",
    BTN_HELP: "help",
}
