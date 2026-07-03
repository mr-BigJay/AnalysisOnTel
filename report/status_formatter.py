"""Format quick market status for Telegram."""

from __future__ import annotations

from market.status import MarketStatus
from market.types import Trend
from report.rtl import bullet, divider, ltr, row, rtl, section, wrap_message


def _trend_display(trend: Trend) -> str:
    mapping = {
        Trend.BULLISH: "صعودی 📈",
        Trend.BEARISH: "نزولی 📉",
        Trend.NEUTRAL: "خنثی ➖",
    }
    return mapping[trend]


def format_status_report(status: MarketStatus) -> str:
    tf_lines = [
        row(tf.label, _trend_display(tf.trend))
        for tf in status.timeframes
    ]

    body = "\n".join(
        [
            row("قیمت الان", ltr(f"${status.price:,.1f}")),
            "",
            divider(),
            "",
            *tf_lines,
            "",
            divider(),
            bullet("روزانه جهت اصلی است — ۱۵دقیقه فقط نمای سریع"),
        ]
    )

    text = "\n".join(
        [
            section("📡 وضعیت لحظه‌ای BTC"),
            body,
            f"\n🕐 {ltr(status.generated_at)}",
            "\n<i>AnalysisOnTel</i>",
        ]
    )
    return wrap_message(text)
