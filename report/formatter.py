"""Persian report formatting for Telegram."""

from __future__ import annotations

from market.analysis import MarketReport, Trend, TradeScenario


def _trend_fa(trend: Trend) -> str:
    return {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[trend.value]


def _fmt_tf_block(report: MarketReport, tf_key: str) -> str:
    tf = {"1d": report.daily, "4h": report.h4, "1h": report.h1}[tf_key]
    lines = [
        f"━━ {tf.label} ━━",
        f"روند: {_trend_fa(tf.trend)} | قیمت: ${tf.price:,.1f}",
        f"RSI: {tf.rsi} | MACD: {tf.macd_hist:+.2f}",
        f"حمایت: ${tf.support:,.0f} | مقاومت: ${tf.resistance:,.0f}",
        f"امتیاز: {tf.score}/100",
    ]
    if tf.is_ranging:
        lines.append("⚠️ بازار در رنج")
    return "\n".join(lines)


def _fmt_scenario(scenario: TradeScenario) -> str:
  side = "لانگ 🟢" if scenario.bias == "long" else "شورت 🔴"
  return "\n".join(
      [
          f"📌 سناریو پیشنهادی ({side})",
          scenario.condition,
          f"→ {side} بگیر",
          f"دلیل: {scenario.reason}",
          f"حد ضرر: ${scenario.stop_loss:,.0f}",
          f"هدف سود: ${scenario.take_profit:,.0f}",
          f"اطمینان: {scenario.confidence}%",
          f"باطل شدن: بسته شدن ۴H {'زیر' if scenario.bias == 'long' else 'بالای'} ${scenario.stop_loss:,.0f}",
      ]
  )


def format_report(report: MarketReport) -> str:
    parts = [
        "📊 <b>گزارش لحظه‌ای BTC</b>",
        f"🕐 {report.generated_at}",
        "",
        *report.summary_lines,
        "",
        _fmt_tf_block(report, "1d"),
        "",
        _fmt_tf_block(report, "4h"),
        "",
        _fmt_tf_block(report, "1h"),
        "",
        "━━ جمع‌بندی ━━",
    ]

    if report.scenario and report.action in ("full", "watch"):
        parts.append(_fmt_scenario(report.scenario))
        if report.action == "watch":
            parts.append("\n⚠️ هنوز ورود قطعی نیست — فقط نظارت")
    else:
        parts.append("⏳ فعلاً ورود توصیه نمی‌شود — صبر کن")

    parts.append(f"\nامتیاز کیفیت کلی: <b>{report.quality_score}/100</b>")
    parts.append("\n<i>AnalysisOnTel — داده: Kraken | تحلیل احتمالی، نه قطعیت</i>")

    return "\n".join(parts)


def format_candle_close_alert(report: MarketReport, timeframe_label: str) -> str:
    """Shorter alert when a candle closes on a specific timeframe."""
    tf_map = {"روزانه": report.daily, "۴ ساعته": report.h4, "۱ ساعته": report.h1}
    tf = tf_map.get(timeframe_label, report.h1)

    lines = [
        f"🔔 <b>کندل {timeframe_label} بسته شد</b>",
        f"🕐 {report.generated_at}",
        f"روند {_trend_fa(tf.trend)} | قیمت: ${tf.price:,.1f}",
        f"امتیاز: {tf.score}/100",
        "",
    ]
    if report.scenario and report.action == "full":
        side = "لانگ" if report.scenario.bias == "long" else "شورت"
        lines.append(f"✅ سناریو {side}: {report.scenario.condition}")
    else:
        lines.append("⏳ فعلاً صبر — سیگنال قوی نیست")

    return "\n".join(lines)
