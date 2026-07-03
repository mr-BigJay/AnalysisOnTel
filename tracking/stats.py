"""Format performance statistics for Telegram."""

from __future__ import annotations

from tracking.database import count_by_outcome, count_pending, fetch_recent


OUTCOME_FA = {
    "win": "برد ✅",
    "loss": "باخت ❌",
    "inconclusive": "نامشخص ⏸",
    "no_entry": "بدون ورود 🚫",
    "pending": "در انتظار ⏳",
}


def _win_rate(counts: dict[str, int]) -> tuple[int, int, float | None]:
    wins = counts.get("win", 0)
    losses = counts.get("loss", 0)
    decided = wins + losses
    if decided == 0:
        return wins, losses, None
    return wins, losses, (wins / decided) * 100


def _format_period(title: str, days: int | None) -> list[str]:
    counts = count_by_outcome(days)
    wins, losses, rate = _win_rate(counts)
    total = sum(counts.values())
    lines = [f"<b>{title}</b>"]
    if total == 0:
        lines.append("هنوز داده کافی نیست")
        return lines
    lines.append(f"کل ارزیابی‌شده: {total}")
    lines.append(f"برد: {wins} | باخت: {losses}")
    if rate is not None:
        lines.append(f"Win Rate: <b>{rate:.1f}%</b>")
    else:
        lines.append("Win Rate: — (هنوز برد/باخت قطعی نیست)")
    for key in ("inconclusive", "no_entry"):
        if counts.get(key):
            lines.append(f"{OUTCOME_FA[key]}: {counts[key]}")
    return lines


def format_stats_report() -> str:
    pending = count_pending()
    parts = [
        "📈 <b>آمار عملکرد ربات</b>",
        "",
        *_format_period("۷ روز اخیر", 7),
        "",
        *_format_period("۳۰ روز اخیر", 30),
        "",
        *_format_period("کل دوره", None),
        "",
        f"پیش‌بینی‌های در انتظار ارزیابی: <b>{pending}</b>",
        "",
        "━━ آخرین پیش‌بینی‌ها ━━",
    ]

    recent = fetch_recent(5)
    if not recent:
        parts.append("هنوز پیش‌بینی ثبت نشده")
    else:
        for row in recent:
            outcome = OUTCOME_FA.get(row.outcome, row.outcome)
            parts.append(
                f"#{row.id} {row.created_at} | {row.bias} | {outcome}"
            )
            if row.outcome_note:
                parts.append(f"↳ {row.outcome_note}")

    parts.append("")
    parts.append("<i>ارزیابی خودکار هر ۴ ساعت پس از ثبت پیش‌بینی</i>")
    return "\n".join(parts)
