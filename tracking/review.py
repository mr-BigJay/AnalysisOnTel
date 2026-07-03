"""Prediction review — compare forecast vs actual outcome."""

from __future__ import annotations

from tracking.database import PredictionRow, fetch_recent

OUTCOME_FA = {
    "win": "برد ✅",
    "loss": "باخت ❌",
    "inconclusive": "نامشخص ⏸",
    "no_entry": "بدون ورود 🚫",
    "pending": "در انتظار ⏳",
}

BIAS_FA = {"long": "لانگ", "short": "شورت", "wait": "صبر"}


def _find_last_reviewable() -> PredictionRow | None:
    for row in fetch_recent(20):
        if row.outcome != "pending":
            return row
    return None


def format_review_report() -> str:
    row = _find_last_reviewable()
    if not row:
        pending = [r for r in fetch_recent(5) if r.outcome == "pending"]
        if pending:
            p = pending[0]
            return "\n".join(
                [
                    "📋 <b>بازبینی پیش‌بینی</b>",
                    "",
                    f"پیش‌بینی #{p.id} ({p.created_at}) هنوز ارزیابی نشده.",
                    f"جهت: <b>{BIAS_FA.get(p.bias, p.bias)}</b>",
                    f"قیمت آن زمان: ${p.price_at_signal:,.1f}",
                    "",
                    f"ارزیابی بعد از: {p.eval_after} UTC",
                    "",
                    "<i>بعد از ۴ ساعت نتیجه واقعی ثبت می‌شود.</i>",
                ]
            )
        return "📋 هنوز پیش‌بینی ثبت نشده. یک بار /report بزنید."

    lines = [
        "📋 <b>بازبینی پیش‌بینی</b>",
        "",
        f"<b>پیش‌بینی من ({row.created_at}):</b>",
        f"جهت: {BIAS_FA.get(row.bias, row.bias)} | action: {row.action}",
        f"قیمت آن زمان: ${row.price_at_signal:,.1f}",
    ]

    if row.entry_low and row.entry_high:
        lines.append(f"ورود پیشنهادی: ${row.entry_low:,.0f} – ${row.entry_high:,.0f}")
    if row.stop_loss and row.take_profit:
        lines.append(f"SL: ${row.stop_loss:,.0f} | TP: ${row.take_profit:,.0f}")

    lines.extend(
        [
            f"روند: روزانه {row.daily_trend} | ۴H {row.h4_trend} | ۱H {row.h1_trend}",
            "",
            f"<b>نتیجه واقعی ({row.outcome_at or '—'}):</b>",
            f"{OUTCOME_FA.get(row.outcome, row.outcome)}",
        ]
    )

    if row.outcome_price is not None:
        delta = ((row.outcome_price - row.price_at_signal) / row.price_at_signal) * 100
        lines.append(f"قیمت نهایی: ${row.outcome_price:,.1f} ({delta:+.2f}%)")

    if row.outcome_note:
        lines.append(f"توضیح: {row.outcome_note}")

    lines.append("")
    lines.append("<i>این بازبینی پایه خود-اصلاح ربات است.</i>")
    return "\n".join(lines)
