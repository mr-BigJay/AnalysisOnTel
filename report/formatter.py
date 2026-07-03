"""Persian report formatting for Telegram — clean RTL-friendly layout."""

from __future__ import annotations

from market.analysis import MarketReport, TradeScenario
from market.types import Trend


def _trend_fa(trend: Trend) -> str:
    return {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[trend.value]


def _ltr(text: str) -> str:
    """Wrap LTR content to reduce RTL/LTR mixing issues in Telegram."""
    return f"\u200e{text}"


def _section(title: str) -> str:
    return f"\n<b>{title}</b>"


def _line(label: str, value: str) -> str:
    return f"• {label}: {_ltr(value)}"


def _fmt_summary(report: MarketReport) -> str:
    lines = [
        _section("خلاصه سریع"),
        _line("قیمت الان", f"${report.h1.price:,.1f}"),
        _line("روزانه", _trend_fa(report.daily.trend)),
        _line("۴ ساعته", _trend_fa(report.h4.trend)),
        _line("۱ ساعته", _trend_fa(report.h1.trend)),
        _line("امتیاز کیفیت", f"{report.quality_score}/100"),
    ]

    if report.daily.trend.value == "bullish":
        lines.append("• جهت مجاز: لانگ یا صبر")
        lines.append("• ⛔ شورت = خلاف روند بلندمدت")
    elif report.daily.trend.value == "bearish":
        lines.append("• جهت مجاز: شورت یا صبر")
        lines.append("• ⛔ لانگ = خلاف روند بلندمدت")
    else:
        lines.append("• جهت روزانه: نامشخص — صبر کن")

    if report.event_risk and report.event_risk_note:
        lines.append(f"• ⚠️ رویداد پرریسک: {_ltr(report.event_risk_note)}")

    action_fa = {
        "full": "✅ شرایط ورود مناسب",
        "watch": "👀 فقط نظارت",
        "wait": "⏸ صبر (رنج/نامناسب)",
        "no_signal": "⏳ سیگنال قوی نیست",
    }
    lines.append(f"• وضعیت: {action_fa.get(report.action, report.action)}")
    return "\n".join(lines)


def _fmt_tf_block(label: str, tf) -> str:
    lines = [
        _section(label),
        _line("روند", _trend_fa(tf.trend)),
        _line("قیمت", f"${tf.price:,.1f}"),
        _line("RSI", str(tf.rsi)),
        _line("MACD", f"{tf.macd_hist:+.1f}"),
        _line("حمایت", f"${tf.support:,.0f}"),
        _line("مقاومت", f"${tf.resistance:,.0f}"),
        _line("حجم", f"{tf.volume_ratio}x میانگین"),
        _line("امتیاز", f"{tf.score}/100"),
    ]
    if tf.is_ranging:
        lines.append("• ⚠️ بازار در رنج")
    return "\n".join(lines)


def _fmt_derivatives(report: MarketReport) -> str:
    d = report.derivatives
    lines = [_section("مشتقات و احساسات")]
    if d.funding_rate is not None:
        lines.append(_line("نرخ فاندینگ", f"{d.funding_rate * 100:.4f}%"))
    if d.open_interest_usd is not None:
        lines.append(_line("اوپن اینترست", f"${d.open_interest_usd / 1e9:.2f}B"))
    if d.long_short_ratio is not None:
        lines.append(_line("لانگ/شورت", f"{d.long_short_ratio:.2f}"))
    if d.fear_greed_value is not None:
        lines.append(_line("ترس و طمع", f"{d.fear_greed_value} ({d.fear_greed_label})"))
    return "\n".join(lines)


def _fmt_checklist(report: MarketReport) -> str:
    c = report.checklist
    lines = [
        _section("چک‌لیست کیفیت"),
        _line("نتیجه", f"{c.passed}/{c.total} — {c.score}%"),
    ]
    failed = [(label, note) for label, ok, note in c.items if not ok]
    if failed:
        lines.append("• موارد ضعیف:")
        for label, note in failed:
            lines.append(f"  ❌ {label} — {_ltr(note)}")
    else:
        lines.append("• ✅ همه موارد تأیید شد")
    return "\n".join(lines)


def _fmt_scenario(scenario: TradeScenario) -> str:
    side = "لانگ 🟢" if scenario.bias == "long" else "شورت 🔴"
    lines = [
        _section(f"سناریو پیشنهادی — {side}"),
        f"• شرط ورود:",
        f"  {_ltr(scenario.condition)}",
        _line("حد ضرر", f"${scenario.stop_loss:,.0f}"),
        _line("هدف سود", f"${scenario.take_profit:,.0f}"),
        _line("اطمینان", f"{scenario.confidence}%"),
        f"• دلیل: {scenario.reason}",
        f"• باطل شدن: بسته ۴H {'زیر' if scenario.bias == 'long' else 'بالای'} {_ltr(f'${scenario.stop_loss:,.0f}')}",
    ]
    return "\n".join(lines)


def format_report(report: MarketReport, diff_block: str | None = None) -> str:
    parts = [
        "📊 <b>گزارش لحظه‌ای BTC</b>",
        f"🕐 {_ltr(report.generated_at)}",
    ]
    if diff_block:
        parts.append(diff_block)
    parts.extend([
        _fmt_summary(report),
        _fmt_tf_block("روزانه", report.daily),
        _fmt_tf_block("۴ ساعته", report.h4),
        _fmt_tf_block("۱ ساعته", report.h1),
        _fmt_derivatives(report),
        _fmt_checklist(report),
    ])

    if report.scenario and report.action in ("full", "watch"):
        parts.append(_fmt_scenario(report.scenario))
        if report.action == "watch":
            parts.append("\n⚠️ هنوز ورود قطعی نیست — فقط نظارت")
    else:
        parts.append(_section("جمع‌بندی"))
        parts.append("⏳ فعلاً ورود توصیه نمی‌شود — صبر کن")

    parts.append(f"\n<i>AnalysisOnTel</i>")
    return "\n".join(parts)


def format_candle_close_alert(report: MarketReport, timeframe_label: str) -> str:
    tf_map = {"روزانه": report.daily, "۴ ساعته": report.h4, "۱ ساعته": report.h1}
    tf = tf_map.get(timeframe_label, report.h1)

    lines = [
        f"🔔 <b>کندل {timeframe_label} بسته شد</b>",
        f"🕐 {_ltr(report.generated_at)}",
        _line("روند", _trend_fa(tf.trend)),
        _line("قیمت", f"${tf.price:,.1f}"),
        _line("چک‌لیست", f"{report.checklist.passed}/{report.checklist.total}"),
        "",
    ]
    if report.scenario and report.action == "full":
        side = "لانگ" if report.scenario.bias == "long" else "شورت"
        lines.append(f"✅ سناریو {side}")
        lines.append(_ltr(report.scenario.condition))
    else:
        lines.append("⏳ فعلاً صبر — سیگنال قوی نیست")

    return "\n".join(lines)
