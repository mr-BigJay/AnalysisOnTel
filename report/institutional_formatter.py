"""Institutional Persian report formatter for Telegram — RTL layout."""

from __future__ import annotations

from market.analysis import MarketReport
from market.institutional import IndicatorSignal, InstitutionalBrief, SMCScenario, TechnicalBlock
from report.rtl import bullet, divider, ltr, row, section, wrap_message


def _sentiment_fa(s: str) -> str:
    return {"bullish": "صعودی 🟢", "bearish": "نزولی 🔴", "neutral": "خنثی ⚪"}.get(s, s)


def _fmt_signal(sig: IndicatorSignal) -> str:
    return bullet(
        f"{_sentiment_fa(sig.sentiment)} <b>{sig.label}</b> ({sig.timeframe})\n"
        f"   {sig.note}"
    )


def _fmt_technical_block(block: TechnicalBlock) -> str:
    levels = "\n".join(
        [
            bullet(f"حمایت: {ltr(block.support_zone)}"),
            bullet(f"مقاومت: {ltr(block.resistance_zone)}"),
        ]
    )
    if block.breakout_level:
        levels += f"\n{bullet(f'سطح شکست: {ltr(block.breakout_level)}')}"

    signals = "\n".join(_fmt_signal(s) for s in block.signals)
    return section(
        f"📌 {block.title}",
        f"{block.analysis}\n\n<b>سطوح کلیدی</b>\n{levels}\n\n<b>اندیکاتورها</b>\n{signals}",
    )


def _fmt_news(brief: InstitutionalBrief) -> str:
    if not brief.news_items:
        return section("۱. اخبار و زمینه بازار", bullet("خبری در دسترس نیست"))

    items: list[str] = []
    for i, item in enumerate(brief.news_items):
        if i > 0:
            items.append(divider("·", 16))
        items.append(
            f"<b>{_sentiment_fa(item.sentiment)}</b>\n"
            f"{item.title}\n"
            f"{item.summary}"
        )
        if item.source != "CoinDesk":
            items.append(f"<i>منبع: {item.source}</i>")
    return section("۱. اخبار و زمینه بازار", "\n\n".join(items))


def _fmt_smc(scenario: SMCScenario) -> str:
    risk = "\n⚠️ <b>پرریسک</b>" if scenario.high_risk else ""
    tps = "\n".join(
        bullet(f"هدف {i + 1}: {ltr(f'${tp:,.0f}')}")
        for i, tp in enumerate(scenario.take_profits)
    )
    body = "\n".join(
        [
            bullet(f"شرط: {scenario.condition}"),
            bullet(f"ورود: {ltr(f'${scenario.entry_low:,.0f}–${scenario.entry_high:,.0f}')}"),
            bullet(f"حد ضرر: {ltr(f'${scenario.stop_loss:,.0f}')}"),
            tps,
            bullet(f"نکته: {scenario.note}"),
        ]
    )
    return section(f"{scenario.name} — {scenario.probability}%{risk}", body)


def _fmt_tips(brief: InstitutionalBrief) -> str:
    return section(
        "۳. توصیه معاملاتی",
        f"📈 <b>بلندمدت</b>\n{brief.long_strategy}\n\n"
        f"📊 <b>کوتاه‌مدت</b>\n{brief.short_strategy}",
    )


def _fmt_decision(brief: InstitutionalBrief, report: MarketReport) -> str:
    action_fa = {
        "full": "✅ ورود مناسب",
        "watch": "👀 فقط نظارت",
        "wait": "⏸ صبر",
        "no_signal": "⏳ بدون سیگنال قوی",
    }
    body_lines = [
        row("بلندمدت", brief.long_term_label.replace("بلندمدت: ", "")),
        row("کوتاه‌مدت", brief.short_term_label.replace("کوتاه‌مدت: ", "")),
        row("وضعیت ربات", action_fa.get(report.action, report.action)),
        row("احتمال لانگ", f"{brief.long_probability}%"),
        row("احتمال شورت", f"{brief.short_probability}%"),
        "",
        f"<b>جمع‌بندی</b>\n{brief.decision_text}",
    ]
    if report.daily.trend.value == "bullish":
        body_lines.append("\n⛔ شورت خلاف روند روزانه = پرریسک")
    elif report.daily.trend.value == "bearish":
        body_lines.append("\n⛔ لانگ خلاف روند روزانه = پرریسک")
    return section("۴. تصمیم لحظه‌ای", "\n".join(body_lines))


def format_institutional_report(
    report: MarketReport,
    brief: InstitutionalBrief,
    diff_block: str | None = None,
) -> list[str]:
    """Return report split into Telegram-safe RTL message parts."""
    header = section(
        "📊 گزارش BTC",
        "\n".join(
            [
                f"<b>{brief.headline}</b>",
                f"🕐 {ltr(report.generated_at)}",
                divider(),
                row("کوتاه‌مدت", brief.short_term_label.replace("کوتاه‌مدت: ", "")),
                row("بلندمدت", brief.long_term_label.replace("بلندمدت: ", "")),
                divider(),
                brief.executive_summary,
            ]
        ),
    )

    part1_parts = [wrap_message(header)]
    if diff_block:
        part1_parts.append(wrap_message(diff_block))
    part1_parts.append(wrap_message(_fmt_news(brief)))
    part1 = "\n\n".join(part1_parts)

    part2 = wrap_message(
        "\n\n".join(
            [
                section("۲. سیگنال‌های تکنیکال"),
                _fmt_technical_block(brief.long_term),
                _fmt_technical_block(brief.short_term),
                section(
                    "چک‌لیست کیفیت",
                    "\n".join(
                        [
                            row("نتیجه", f"{report.checklist.passed}/{report.checklist.total}"),
                            row("امتیاز", f"{report.checklist.score}%"),
                            row("کیفیت کلی", f"{report.quality_score}/100"),
                        ]
                    ),
                ),
            ]
        )
    )

    smc_body = "\n\n".join(_fmt_smc(sc) for sc in brief.smc_scenarios)
    part3 = wrap_message(
        "\n\n".join(
            [
                section("سناریوهای SMC/ICT", smc_body),
                _fmt_tips(brief),
                _fmt_decision(brief, report),
                f"\n<i>AnalysisOnTel — 1D + 4H + 1H</i>",
            ]
        )
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
