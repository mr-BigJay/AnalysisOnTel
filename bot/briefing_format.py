"""Format 4-hour comprehensive briefing for Telegram."""

from __future__ import annotations

from market.briefing import BriefingReport
from notifications.messages import ltr, wrap


def _section(title: str) -> str:
    return f"\n<b>{title}</b>\n{'─' * 16}"


def format_briefing_report(report: BriefingReport) -> list[str]:
    header = wrap(
        "\n".join(
            [
                f"📋 <b>{report.headline}</b>",
                f"🕐 {ltr(report.generated_at)}",
                f"روند: کوتاه‌مدت {report.short_trend} | بلندمدت {report.long_trend}",
                "",
                report.summary,
            ]
        )
    )

    if report.momentum_note:
        header += f"\n\n{report.momentum_note}"

    news_lines = [_section("۱. اخبار و کانتکست")]
    for item in report.news:
        news_lines.append(f"• <b>{item.category}</b>\n  {item.title}\n  <i>{item.summary[:200]}</i>")

    lt = report.long_term
    long_ta = [_section(f"۲. سیگنال تکنیکال — {lt.label}")]
    long_ta.append(lt.analysis)
    long_ta.append(
        f"\nحمایت: {ltr(f'${lt.support_zone[0]:,.0f}–${lt.support_zone[1]:,.0f}')}\n"
        f"مقاومت: {ltr(f'${lt.resistance_zone[0]:,.0f}–${lt.resistance_zone[1]:,.0f}')}"
    )
    for name, note in lt.indicators:
        long_ta.append(f"• {name}: {note}")

    st = report.short_term
    short_ta = [_section(f"📌 {st.label}")]
    short_ta.append(st.analysis)
    short_ta.append(
        f"\nحمایت: {ltr(f'${st.support_zone[0]:,.0f}–${st.support_zone[1]:,.0f}')}\n"
        f"مقاومت: {ltr(f'${st.resistance_zone[0]:,.0f}–${st.resistance_zone[1]:,.0f}')}"
    )
    for name, note in st.indicators:
        short_ta.append(f"• {name}: {note}")

    ict = [_section("۳. تحلیل ICT/SMC")]
    if report.bsl:
        ict.append(f"<b>Buy Side Liquidity</b>: {ltr(', '.join(f'${x:,.0f}' for x in report.bsl))}")
    if report.ssl:
        ict.append(f"<b>Sell Side Liquidity</b>: {ltr(', '.join(f'${x:,.0f}' for x in report.ssl))}")
    ict.append("احتمال جمع‌آوری یکی از دو سمت نقدینگی قبل از حرکت اصلی.")

    for sc in report.scenarios:
        tp2_line = f" | TP2: {ltr(f'${sc.tp2:,.0f}')}" if sc.tp2 else ""
        ict.append(
            f"\n<b>{sc.name}</b> ({sc.probability}٪)\n"
            f"{sc.description}\n"
            f"Entry: {ltr(f'${sc.entry_low:,.0f}–${sc.entry_high:,.0f}')}\n"
            f"SL: {ltr(f'${sc.stop_loss:,.0f}')} | TP1: {ltr(f'${sc.tp1:,.0f}')}{tp2_line}\n"
            f"تریگر: {', '.join(sc.triggers)}"
        )

    tips = [_section("۴. استراتژی")]
    tips.append(f"📈 <b>بلندمدت</b>\n{report.long_tips}")
    tips.append(f"\n📊 <b>کوتاه‌مدت</b>\n{report.short_tips}")

    action = [_section("۵. اقدام پیشنهادی")]
    action.append("❌ وسط رنج معامله نکن.")
    for label, px in report.pending_orders:
        action.append(f"• {label}: {ltr(f'${px:,.0f}')}")

    footer = _section("🎯 نظر نهایی")
    footer += (
        f"\n🟢 لانگ: {report.long_prob}٪ | 🔴 شورت: {report.short_prob}٪\n"
        f"{report.final_note}\n\n"
        f"<i>AnalysisOnTel — گزارش ۴ ساعته</i>"
    )

    part1 = "\n".join([header, "\n".join(news_lines), "\n".join(long_ta), "\n".join(short_ta)])
    part2 = "\n".join([wrap("\n".join(ict)), "\n".join(tips), "\n".join(action), footer])

    return _split([part1, wrap(part2)])


def _split(parts: list[str], max_len: int = 3900) -> list[str]:
    out: list[str] = []
    for part in parts:
        part = part.strip()
        if len(part) <= max_len:
            out.append(part)
        else:
            for i in range(0, len(part), max_len):
                out.append(part[i : i + max_len])
    return out
