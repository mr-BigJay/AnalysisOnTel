"""Market news from RSS and contextual sentiment items."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

from market.derivatives import DerivativesSnapshot

logger = logging.getLogger(__name__)

RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"

BULLISH_WORDS = (
    "surge", "rally", "bull", "record", "inflow", "adoption", "approval",
    "etf inflow", "breakout", "upgrade", "growth", "expansion", "investment",
    "institutional", "accumulation",
)
BEARISH_WORDS = (
    "crash", "drop", "fall", "bear", "hack", "fraud", "ponzi", "scam",
    "lawsuit", "ban", "outflow", "selloff", "sell-off", "liquidation",
    "tension", "war", "sanction", "risk", "warning", "plunge", "decline",
)


@dataclass
class NewsItem:
    sentiment: str  # bullish | bearish | neutral
    title: str
    summary: str
    source: str = "CoinDesk"


def _classify_headline(title: str) -> str:
    lower = title.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in lower)
    bear = sum(1 for w in BEARISH_WORDS if w in lower)
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def _persian_summary(title: str, sentiment: str) -> str:
    """Short Persian context from headline keywords."""
    lower = title.lower()
    if "etf" in lower or "institutional" in lower or "inflow" in lower:
        return "جریان سرمایه نهادی می‌تواند تقاضای BTC را تقویت کند."
    if any(w in lower for w in ("ai", "chip", "infrastructure")):
        return "رشد زیرساخت AI معمولاً احساسات ریسک‌پذیری بازار را بهبود می‌دهد."
    if any(w in lower for w in ("fraud", "ponzi", "scam", "hack")):
        return "اخبار کلاهبرداری/امنیتی می‌تواند اعتماد کوتاه‌مدت را کاهش دهد."
    if any(w in lower for w in ("tension", "war", "sanction", "tariff", "geopolit")):
        return "تنش ژئوپلیتیک معمولاً فشار فروش یا نوسان را افزایش می‌دهد."
    if any(w in lower for w in ("surge", "rally", "record", "breakout")):
        return "اخبار مثبت می‌تواند مومنتوم خرید را تقویت کند."
    if any(w in lower for w in ("drop", "fall", "crash", "plunge")):
        return "اخبار منفی می‌تواند فشار فروش کوتاه‌مدت ایجاد کند."
    if sentiment == "bullish":
        return "لحن خبری نسبتاً مثبت برای بازار ریسک است."
    if sentiment == "bearish":
        return "لحن خبری نسبتاً منفی برای بازار ریسک است."
    return "تأثیر مستقیم محدود؛ بیشتر برای احساسات کلی بازار."


def _fetch_rss_items(limit: int = 4) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        resp = requests.get(RSS_URL, timeout=15, headers={"User-Agent": "AnalysisOnTel/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return items
        for item in channel.findall("item")[:limit]:
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            title = re.sub(r"\s+", " ", title_el.text.strip())
            sentiment = _classify_headline(title)
            items.append(
                NewsItem(
                    sentiment=sentiment,
                    title=title,
                    summary=_persian_summary(title, sentiment),
                )
            )
    except Exception:
        logger.warning("RSS news fetch failed", exc_info=True)
    return items


def _derivatives_news(d: DerivativesSnapshot) -> list[NewsItem]:
    items: list[NewsItem] = []
    if d.funding_rate is not None:
        if d.funding_rate > 0.0002:
            items.append(
                NewsItem(
                    sentiment="bearish",
                    title="Funding rate elevated on BTC perps",
                    summary="فاندینگ مثبت بالا نشان‌دهنده لانگ‌های شلوغ و احتمال اصلاح کوتاه‌مدت است.",
                    source="OKX",
                )
            )
        elif d.funding_rate < -0.0001:
            items.append(
                NewsItem(
                    sentiment="bullish",
                    title="Negative funding on BTC perps",
                    summary="فاندینگ منفی می‌تواند نشانه فشار شورت و پتانسیل اسکویز صعودی باشد.",
                    source="OKX",
                )
            )

    if d.fear_greed_value is not None:
        if d.fear_greed_value >= 75:
            items.append(
                NewsItem(
                    sentiment="bearish",
                    title=f"Extreme Greed ({d.fear_greed_value})",
                    summary="شاخص ترس/طمع در منطقه طمع — احتمال اصلاح یا نوسان افزایش می‌یابد.",
                    source="Fear&Greed",
                )
            )
        elif d.fear_greed_value <= 25:
            items.append(
                NewsItem(
                    sentiment="bullish",
                    title=f"Extreme Fear ({d.fear_greed_value})",
                    summary="شاخص ترس/طمع در منطقه ترس — پتانسیل برگشت فنی در صورت تثبیت قیمت.",
                    source="Fear&Greed",
                )
            )
    return items


def _event_news(event_note: str | None) -> list[NewsItem]:
    if not event_note:
        return []
    return [
        NewsItem(
            sentiment="bearish",
            title="High-impact macro event ahead",
            summary=f"رویداد ماکرو نزدیک: {event_note} — نوسان لحظه‌ای محتمل است.",
            source="Calendar",
        )
    ]


def fetch_market_news(
    derivatives: DerivativesSnapshot,
    event_note: str | None = None,
    max_items: int = 5,
) -> list[NewsItem]:
    """Combine RSS headlines with derivatives/macro context."""
    items = _fetch_rss_items(limit=3)
    items.extend(_derivatives_news(derivatives))
    items.extend(_event_news(event_note))

    # Prefer mix of sentiments, dedupe by title prefix
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.title[:40].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique[:max_items]
