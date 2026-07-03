"""Format backtest results for Telegram."""

from __future__ import annotations

import json

from config import DATA_DIR
from backtest.runner import BACKTEST_RESULT_FILE, BacktestResult, run_backtest


def format_backtest_report(result: BacktestResult | None = None) -> str:
    if result is None:
        if BACKTEST_RESULT_FILE.exists():
            payload = json.loads(BACKTEST_RESULT_FILE.read_text(encoding="utf-8"))
            r = payload["result"]
            result = BacktestResult(**r)
        else:
            return "📉 هنوز بکتست اجرا نشده. دستور /backtest"

    lines = [
        "📉 <b>بکتست تاریخی استراتژی</b>",
        f"🕐 {result.run_at}",
        "",
        f"کندل‌های بررسی‌شده: {result.candles_tested}",
        f"سیگنال‌های full: <b>{result.signals}</b>",
        f"برد: {result.wins} | باخت: {result.losses}",
        f"بدون ورود: {result.no_entry} | نامشخص: {result.inconclusive}",
    ]
    if result.win_rate is not None:
        lines.append(f"Win Rate: <b>{result.win_rate:.1f}%</b>")
    else:
        lines.append("Win Rate: —")
    if result.profit_factor is not None:
        lines.append(f"Profit Factor: <b>{result.profit_factor:.2f}</b>")

    lines.extend(
        [
            "",
            "<i>بکتست روی داده Kraken — قوانین فعلی ربات (بدون مشتقات زنده)</i>",
            "<i>گذشته تضمین آینده نیست</i>",
        ]
    )
    return "\n".join(lines)


def run_and_format() -> str:
    result = run_backtest()
    return format_backtest_report(result)
