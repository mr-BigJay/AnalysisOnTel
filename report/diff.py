"""Compare current report with previous snapshot."""

from __future__ import annotations

from market.analysis import MarketReport
from report.rtl import bullet, ltr, section, wrap_message

_TREND_FA = {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}
_ACTION_FA = {
    "full": "ورود مناسب",
    "watch": "نظارت",
    "wait": "صبر",
    "no_signal": "بدون سیگنال",
}


def _fmt_trend(value: str) -> str:
    return _TREND_FA.get(value, value)


def _fmt_action(value: str) -> str:
    return _ACTION_FA.get(value, value)


def _price_change(old: float, new: float) -> str:
    if old == 0:
        return ""
    pct = ((new - old) / old) * 100
    sign = "+" if pct >= 0 else ""
    return f" ({sign}{pct:.2f}%)"


def format_report_diff(report: MarketReport, previous: dict | None) -> str | None:
    """Return Persian HTML diff block, or None if no previous report."""
    if not previous:
        return None

    lines: list[str] = []

    old_price = previous.get("price")
    if old_price and old_price != report.h1.price:
        ch = _price_change(old_price, report.h1.price)
        lines.append(
            bullet(
                f"قیمت: {ltr(f'${old_price:,.1f}')} ← {ltr(f'${report.h1.price:,.1f}')}{ltr(ch)}"
            )
        )

    for key, label, new_val in (
        ("daily_trend", "روزانه", report.daily.trend.value),
        ("h4_trend", "۴ ساعته", report.h4.trend.value),
        ("h1_trend", "۱ ساعته", report.h1.trend.value),
    ):
        old_val = previous.get(key)
        if old_val and old_val != new_val:
            lines.append(
                bullet(f"روند {label}: {_fmt_trend(old_val)} ← {_fmt_trend(new_val)} ⚠️")
            )

    old_action = previous.get("action")
    if old_action and old_action != report.action:
        lines.append(
            bullet(f"وضعیت: {_fmt_action(old_action)} ← {_fmt_action(report.action)}")
        )

    old_q = previous.get("quality_score")
    if old_q is not None and old_q != report.quality_score:
        lines.append(bullet(f"امتیاز کیفیت: {old_q} ← {report.quality_score}"))

    old_c = previous.get("checklist_score")
    if old_c is not None and old_c != report.checklist.score:
        lines.append(bullet(f"چک‌لیست: {old_c}% ← {report.checklist.score}%"))

    prev_scenario = previous.get("scenario")
    if report.scenario and prev_scenario:
        s = report.scenario
        if (
            prev_scenario.get("entry_low") != s.entry_low
            or prev_scenario.get("entry_high") != s.entry_high
        ):
            lines.append(
                bullet(
                    f"ناحیه ورود: {ltr(f'${prev_scenario['entry_low']:,.0f}–${prev_scenario['entry_high']:,.0f}')}"
                    f" ← {ltr(f'${s.entry_low:,.0f}–${s.entry_high:,.0f}')}"
                )
            )
        if prev_scenario.get("stop_loss") != s.stop_loss:
            lines.append(
                bullet(
                    f"حد ضرر: {ltr(f'${prev_scenario['stop_loss']:,.0f}')} ← {ltr(f'${s.stop_loss:,.0f}')}"
                )
            )
        if prev_scenario.get("take_profit") != s.take_profit:
            lines.append(
                bullet(
                    f"هدف سود: {ltr(f'${prev_scenario['take_profit']:,.0f}')} ← {ltr(f'${s.take_profit:,.0f}')}"
                )
            )
    elif report.scenario and not prev_scenario:
        s = report.scenario
        side = "لانگ" if s.bias == "long" else "شورت"
        lines.append(bullet(f"سناریو جدید: {side} — {ltr(f'${s.entry_low:,.0f}–${s.entry_high:,.0f}')}"))
    elif not report.scenario and prev_scenario:
        lines.append(bullet("سناریو قبلی باطل شد"))

    if not lines:
        lines.append(bullet("بدون تغییر مهم"))
    return wrap_message(section("📌 تغییرات نسبت به گزارش قبل", "\n".join(lines)))
