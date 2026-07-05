"""Format BTC status for Telegram."""

from __future__ import annotations

from market.status import MarketStatus
from market.types import Trend
from notifications.messages import ltr, wrap


def _trend_display(trend: Trend) -> str:
    return {
        Trend.BULLISH: "صعودی 📈",
        Trend.BEARISH: "نزولی 📉",
        Trend.NEUTRAL: "خنثی ➖",
    }[trend]


def format_status_report(status: MarketStatus) -> str:
    lines = [
        "📡 <b>وضعیت BTC</b>",
        "─" * 16,
        f"قیمت: {ltr(f'${status.price:,.1f}')}",
        "",
    ]
    for tf in status.timeframes:
        lines.append(f"<b>{tf.label}</b>  {_trend_display(tf.trend)}")
    lines.extend(
        [
            "",
            "─" * 16,
            f"🕐 {ltr(status.generated_at)}",
            "<i>AnalysisOnTel — BTC Alerts</i>",
        ]
    )
    return wrap("\n".join(lines))
