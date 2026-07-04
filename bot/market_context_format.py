"""Format market context (derivatives + macro) for Telegram."""

from __future__ import annotations

from market.context import MarketContextReport, MetricInsight
from notifications.messages import ltr, wrap


def _fmt_metric(m: MetricInsight) -> str:
    return (
        f"<b>{m.title}</b>\n"
        f"مقدار: {ltr(m.value_line) if '$' in m.value_line or '%' in m.value_line else m.value_line}\n"
        f"وضعیت: {m.status}\n"
        f"📖 {m.meaning}\n"
        f"🔮 <i>برداشت:</i> {m.outlook}"
    )


def format_market_context_report(report: MarketContextReport) -> str:
    parts = [
        "🌐 <b>وضعیت بازار BTC</b>",
        "<i>Funding · Fear&Greed · L/S · OI · ماکرو</i>",
        "─" * 16,
    ]
    for i, m in enumerate(report.metrics):
        if i > 0:
            parts.append("")
        parts.append(_fmt_metric(m))
    parts.extend(
        [
            "",
            "─" * 16,
            f"🕐 {ltr(report.generated_at)}",
            "<i>AnalysisOnTel — اطلاعاتی، نه سیگنال قطعی</i>",
        ]
    )
    return wrap("\n".join(parts))
