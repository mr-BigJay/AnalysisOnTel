"""Format technical analysis report for Telegram."""

from __future__ import annotations

from market.technical import TechnicalReport
from notifications.messages import ltr, wrap


def _section(title: str) -> str:
    return f"\n<b>{title}</b>\n{'─' * 16}"


def format_technical_report(report: TechnicalReport) -> list[str]:
    """Return 2–3 Telegram HTML message parts."""
    header = wrap(
        "\n".join(
            [
                "📊 <b>تحلیل تکنیکال BTC</b>",
                "<i>گزارش مجزا — Technical Analysis</i>",
                f"🕐 {ltr(report.generated_at)}",
                f"💰 قیمت: {ltr(f'${report.price:,.1f}')}",
            ]
        )
    )

    trend_lines = [_section("📈 روند (Trend)")]
    for tf in report.timeframes:
        trend_lines.append(
            f"<b>{tf.label}</b>: {tf.trend}\n"
            f"  {tf.trend_note}\n"
            f"  ساختار: {tf.structure}"
        )

    sr = _section("🧱 حمایت و مقاومت")
    sr += (
        f"\n• نزدیک: حمایت {ltr(f'${report.nearest_support:,.0f}')} | "
        f"مقاومت {ltr(f'${report.nearest_resistance:,.0f}')}"
    )
    if report.supports:
        sr += f"\n• حمایت‌ها: {ltr(', '.join(f'${s:,.0f}' for s in report.supports))}"
    if report.resistances:
        sr += f"\n• مقاومت‌ها: {ltr(', '.join(f'${r:,.0f}' for r in report.resistances))}"

    pa = _section("⚡ پرایس اکشن")
    pa += f"\n{report.price_action}"

    classic = _section("📐 الگوهای کلاسیک")
    classic += f"\n{report.classic_pattern}"

    candle = _section("🕯 کندل استیک")
    candle += f"\n({report.candle_tf}) {report.candle_pattern}"

    vol = _section("📊 حجم (Volume)")
    vol += f"\n{report.volume_note}"

    part1 = "\n".join([header, "\n".join(trend_lines), sr, pa])

    ind = [_section("📉 اندیکاتورها (۱H)")]
    for name, val, sig in report.indicators:
        ind.append(f"• <b>{name}</b>: {ltr(val)} — {sig}")

    summary = _section("🎯 جمع‌بندی")
    summary += f"\n{report.summary}"

    part2 = "\n".join([classic, candle, vol, "\n".join(ind), summary])
    part2 += "\n\n<i>AnalysisOnTel — تحلیل اطلاعاتی</i>"

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
