"""Fetch and interpret non-TF market context (derivatives + macro)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from config import FNG_EXTREME_FEAR, FNG_EXTREME_GREED, FUNDING_EXTREME
from market.derivatives import fetch_derivatives
from market.events import get_event_risk


@dataclass
class MetricInsight:
    title: str
    value_line: str
    status: str  # emoji + short label
    meaning: str
    outlook: str


@dataclass
class MarketContextReport:
    generated_at: str
    metrics: list[MetricInsight]


def _interpret_funding(rate: float | None) -> MetricInsight:
    if rate is None:
        return MetricInsight(
            "Funding Rate",
            "در دسترس نیست",
            "⚪ نامشخص",
            "داده فاندینگ OKX دریافت نشد.",
            "—",
        )

    pct = rate * 100
    value = f"{pct:.4f}% (هر ~۸ ساعت OKX)"

    if rate >= FUNDING_EXTREME:
        return MetricInsight(
            "Funding Rate",
            value,
            "🔴 مثبت افراطی",
            "لانگ‌ها به شورت‌ها پول می‌دهند — بازار شلوغ سمت لانگ است.",
            "احتمال اصلاح کوتاه‌مدت یا اسکویز لانگ‌ها بیشتر است. ورود لانگ تهاجمی توصیه نمی‌شود.",
        )
    if rate <= -FUNDING_EXTREME:
        return MetricInsight(
            "Funding Rate",
            value,
            "🟢 منفی افراطی",
            "شورت‌ها به لانگ‌ها پول می‌دهند — فشار شورت غالب است.",
            "پتانسیل اسکویز صعودی وجود دارد، اما هنوز تأیید قیمت لازم است.",
        )
    if rate > 0.0001:
        return MetricInsight(
            "Funding Rate",
            value,
            "🟡 مثبت ملایم",
            "تمایل جزئی به لانگ در پوزیشن‌های فیوچر.",
            "روند صعودی می‌تواند ادامه یابد؛ در صورت جهش بیشتر فاندینگ، احتیاط کن.",
        )
    if rate < -0.00005:
        return MetricInsight(
            "Funding Rate",
            value,
            "🟡 منفی ملایم",
            "فشار جزئی روی شورت‌ها.",
            "احتمال برگشت فنی صعودی بیشتر از حالت مثبت شدید است.",
        )
    return MetricInsight(
        "Funding Rate",
        value,
        "⚪ خنثی",
        "فاندینگ نزدیک صفر — تعادل نسبی بین لانگ و شورت.",
        "سیگنال جهت‌دار قوی از فاندینگ نمی‌دهد؛ به قیمت و ساختار تکیه کن.",
    )


def _interpret_fng(value: int | None, label: str | None) -> MetricInsight:
    if value is None:
        return MetricInsight(
            "Fear & Greed",
            "در دسترس نیست",
            "⚪ نامشخص",
            "شاخص ترس و طمع دریافت نشد.",
            "—",
        )

    lbl = label or ""
    value_line = f"{value} — {lbl} (روزانه)"

    if value <= FNG_EXTREME_FEAR:
        return MetricInsight(
            "Fear & Greed",
            value_line,
            "🟢 ترس شدید",
            "بازار در حالت ترس افراطی — فروش احساسی غالب است.",
            "معمولاً فرصت برگشت میانی در صورت تثبیت قیمت؛ عجله در شورت کمتر توصیه می‌شود.",
        )
    if value < 45:
        return MetricInsight(
            "Fear & Greed",
            value_line,
            "🟡 ترس",
            "احساسات منفی اما نه افراطی.",
            "روند نزولی می‌تواند ادامه یابد؛ منتظر سیگنال فنی برای برگشت باش.",
        )
    if value <= 55:
        return MetricInsight(
            "Fear & Greed",
            value_line,
            "⚪ خنثی",
            "بازار بین ترس و طمع — بدون افراط.",
            "جهت از احساسات مشخص نیست؛ ساختار قیمت مهم‌تر است.",
        )
    if value < FNG_EXTREME_GREED:
        return MetricInsight(
            "Fear & Greed",
            value_line,
            "🟡 طمع",
            "تمایل به ریسک‌پذیری بیشتر در بازار.",
            "ادامه صعود ممکن است؛ حد ضرر و مدیریت ریسک ضروری است.",
        )
    return MetricInsight(
        "Fear & Greed",
        value_line,
        "🔴 طمع شدید",
        "بازار در حالت طمع افراطی — احتمال خرید بیش از حد.",
        "احتمال اصلاح یا نوسان تیز بیشتر است؛ تعقیب قیمت پرریسک است.",
    )


def _interpret_ls(ratio: float | None) -> MetricInsight:
    if ratio is None:
        return MetricInsight(
            "Long/Short Ratio",
            "در دسترس نیست",
            "⚪ نامشخص",
            "نسبت لانگ/شورت OKX دریافت نشد.",
            "—",
        )

    value_line = f"{ratio:.2f} (OKX — 1D)"

    if ratio >= 2.0:
        return MetricInsight(
            "Long/Short Ratio",
            value_line,
            "🔴 لانگ غالب",
            "اکثریت حساب‌ها لانگ هستند — positioning یک‌طرفه.",
            "از دید contrarian، فشار فروش/اصلاح احتمال بیشتری دارد.",
        )
    if ratio >= 1.3:
        return MetricInsight(
            "Long/Short Ratio",
            value_line,
            "🟡 تمایل لانگ",
            "لانگ‌ها بیشتر از شورت‌ها اما نه افراطی.",
            "هم‌جهت با روند صعودی؛ در صورت شکست سطح، لانگ‌ها آسیب‌پذیرند.",
        )
    if ratio <= 0.7:
        return MetricInsight(
            "Long/Short Ratio",
            value_line,
            "🟢 شورت غالب",
            "اکثریت حساب‌ها شورت — positioning یک‌طرفه.",
            "پتانسیل اسکویز صعودی در صورت حرکت خلاف انتظار.",
        )
    if ratio <= 0.9:
        return MetricInsight(
            "Long/Short Ratio",
            value_line,
            "🟡 تمایل شورت",
            "شورت‌ها کمی بیشتر از لانگ‌ها.",
            "فشار نزولی احتمال بیشتر؛ شکست حمایت می‌تواند تند باشد.",
        )
    return MetricInsight(
        "Long/Short Ratio",
        value_line,
        "⚪ متعادل",
        "تقریباً تعادل بین لانگ و شورت.",
        "جهت از positioning مشخص نیست.",
    )


def _interpret_oi(oi_usd: float | None) -> MetricInsight:
    if oi_usd is None:
        return MetricInsight(
            "Open Interest",
            "در دسترس نیست",
            "⚪ نامشخص",
            "اوپن اینترست OKX دریافت نشد.",
            "—",
        )

    billions = oi_usd / 1e9
    value_line = f"${billions:.2f}B (لحظه‌ای OKX)"

    if billions >= 2.5:
        return MetricInsight(
            "Open Interest",
            value_line,
            "🟡 OI بالا",
            "سرمایه زیادی در فیوچر BTC قفل است — بازار فعال.",
            "حرکت‌های بزرگ می‌توانند تند باشند (liquidation cascade). جهت را از قیمت + funding بگیر.",
        )
    if billions >= 1.5:
        return MetricInsight(
            "Open Interest",
            value_line,
            "⚪ OI متوسط",
            "مشارکت نسبتاً سالم در مشتقات.",
            "تغییر OI (افزایش/کاهش) مهم‌تر از عدد مطلق است — فعلاً snapshot است.",
        )
    return MetricInsight(
        "Open Interest",
        value_line,
        "🟡 OI پایین",
        "مشارکت کمتر در فیوچر — حرکت‌ها ممکن است ضعیف‌تر باشند.",
        "شکست‌های قوی کمتر محتمل؛ رنج بیشتر دیده می‌شود.",
    )


def _interpret_macro(risky: bool, note: str | None) -> MetricInsight:
    if risky and note:
        return MetricInsight(
            "رویداد ماکرو",
            note,
            "🔴 پرریسک نزدیک",
            "رویداد اقتصادی مهم USD/EUR در ۴ ساعت آینده.",
            "نوسان لحظه‌ای محتمل — ورود با حجم بالا یا بدون SL توصیه نمی‌شود.",
        )
    return MetricInsight(
        "رویداد ماکرو",
        "رویداد پرریسک در ۴ ساعت آینده نیست",
        "🟢 آرام",
        "تقویم اقتصادی فعلاً رویداد با تأثیر بالا نزدیک ندارد.",
        "ریسک ماکرو کوتاه‌مدت پایین‌تر — تمرکز روی تکنیکال مجاز است.",
    )


def fetch_market_context() -> MarketContextReport:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    d = fetch_derivatives()
    risky, note = get_event_risk(hours_ahead=4)

    metrics = [
        _interpret_funding(d.funding_rate),
        _interpret_fng(d.fear_greed_value, d.fear_greed_label),
        _interpret_ls(d.long_short_ratio),
        _interpret_oi(d.open_interest_usd),
        _interpret_macro(risky, note),
    ]
    return MarketContextReport(generated_at=now, metrics=metrics)
