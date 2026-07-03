"""Institutional Persian report formatter for Telegram."""

from __future__ import annotations

from market.analysis import MarketReport
from market.institutional import IndicatorSignal, InstitutionalBrief, SMCScenario, TechnicalBlock


def _ltr(text: str) -> str:
    return f"\u200e{text}"


def _section(title: str) -> str:
    return f"\n<b>{title}</b>"


def _sentiment_fa(s: str) -> str:
    return {"bullish": "صعودی 🟢", "bearish": "نزولی 🔴", "neutral": "خنثی ⚪"}.get(s, s)


def _fmt_signal(sig: IndicatorSignal) -> str:
    return (
        f"• {_sentiment_fa(sig.sentiment)} {sig.label} ({sig.timeframe}): "
        f"{sig.note}"
    )


def _fmt_technical_block(block: TechnicalBlock) -> str:
    lines = [
        _section(f"📌 {block.title}"),
        f"{block.analysis}",
        f"\n<b>سطوح کلیدی:</b>",
        f"• حمایت: {_ltr(block.support_zone)}",
        f"• مقاومت: {_ltr(block.resistance_zone)}",
    ]
    if block.breakout_level:
        lines.append(f"• سطح شکست: {_ltr(block.breakout_level)}")
    lines.append("\n<b>اندیکاتورها:</b>")
    lines.extend(_fmt_signal(s) for s in block.signals)
    return "\n".join(lines)


def _fmt_news(brief: InstitutionalBrief) -> str:
    lines = [_section("۱. اخبار و زمینه بازار")]
    if not brief.news_items:
        lines.append("• خبری در دسترس نیست — فقط داده مشتقات/تقویم")
        return "\n".join(lines)
    for item in brief.news_items:
        lines.append(f"\n<b>{_sentiment_fa(item.sentiment)}</b> {item.title}")
        lines.append(f"{item.summary}")
        if item.source != "CoinDesk":
            lines.append(f"<i>منبع: {item.source}</i>")
    return "\n".join(lines)


def _fmt_smc(scenario: SMCScenario) -> str:
    risk = " ⚠️ پرریسک" if scenario.high_risk else ""
    side = "لانگ" if scenario.bias == "long" else "شورت"
    tps = " | ".join(_ltr(f"TP{i+1}: ${tp:,.0f}") for i, tp in enumerate(scenario.take_profits))
    return "\n".join(
        [
            _section(f"{scenario.name} ({scenario.probability}%){risk}"),
            f"• شرط: {scenario.condition}",
            f"• Entry: {_ltr(f'${scenario.entry_low:,.0f}–${scenario.entry_high:,.0f}')}",
            f"• Stop: {_ltr(f'${scenario.stop_loss:,.0f}')}",
            f"• {tps}",
            f"• نکته: {scenario.note}",
        ]
    )


def _fmt_tips(brief: InstitutionalBrief) -> str:
    return "\n".join(
        [
            _section("۳. توصیه معاملاتی"),
            f"📈 <b>بلندمدت</b>\n{brief.long_strategy}",
            f"\n📊 <b>کوتاه‌مدت</b>\n{brief.short_strategy}",
        ]
    )


def _fmt_decision(brief: InstitutionalBrief, report: MarketReport) -> str:
    action_fa = {
        "full": "✅ ورود مناسب",
        "watch": "👀 فقط نظارت",
        "wait": "⏸ صبر",
        "no_signal": "⏳ بدون سیگنال قوی",
    }
    lines = [
        _section("۴. تصمیم لحظه‌ای"),
        f"• {brief.long_term_label} | {brief.short_term_label}",
        f"• وضعیت ربات: {action_fa.get(report.action, report.action)}",
        f"• احتمال لانگ: {brief.long_probability}% | شورت: {brief.short_probability}%",
        f"\n<b>جمع‌بندی:</b>\n{brief.decision_text}",
    ]
    if report.daily.trend.value == "bullish":
        lines.append("\n⛔ شورت خلاف روند روزانه = پرریسک")
    elif report.daily.trend.value == "bearish":
        lines.append("\n⛔ لانگ خلاف روند روزانه = پرریسک")
    return "\n".join(lines)


def format_institutional_report(
    report: MarketReport,
    brief: InstitutionalBrief,
    diff_block: str | None = None,
) -> list[str]:
    """Return report split into Telegram-safe message parts."""
    part1 = "\n".join(
        [
            f"<b>{brief.headline}</b>",
            f"🕐 {_ltr(report.generated_at)}",
            f"{brief.short_term_label} | {brief.long_term_label}",
            "",
            brief.executive_summary,
            diff_block or "",
            _fmt_news(brief),
        ]
    ).strip()

    part2 = "\n".join(
        [
            _section("۲. سیگنال‌های تکنیکال"),
            _fmt_technical_block(brief.long_term),
            "",
            _fmt_technical_block(brief.short_term),
            _section("چک‌لیست کیفیت"),
            f"• نتیجه: {report.checklist.passed}/{report.checklist.total} — {report.checklist.score}%",
            f"• امتیاز کلی: {report.quality_score}/100",
        ]
    )

    smc_parts = [_section("سناریوهای SMC/ICT")]
    for sc in brief.smc_scenarios:
        smc_parts.append(_fmt_smc(sc))

    part3 = "\n".join(
        [
            "\n".join(smc_parts),
            _fmt_tips(brief),
            _fmt_decision(brief, report),
            "\n<i>AnalysisOnTel — 1D + 4H + 1H</i>",
        ]
    )

    return split_telegram_messages([part1, part2, part3])


def split_telegram_messages(parts: list[str], max_len: int = 3900) -> list[str]:
    """Merge and split parts so each message fits Telegram HTML limit."""
    messages: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            messages.append(part)
            continue
        # Split long parts on double newlines
        chunks: list[str] = []
        current = ""
        for block in part.split("\n\n"):
            candidate = f"{current}\n\n{block}".strip() if current else block
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(block) <= max_len:
                    current = block
                else:
                    for i in range(0, len(block), max_len):
                        chunks.append(block[i : i + max_len])
                    current = ""
        if current:
            chunks.append(current)
        messages.extend(chunks)
    return messages
