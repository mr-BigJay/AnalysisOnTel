"""BTC-related news headlines for briefing reports."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://cointelegraph.com/rss/tag/bitcoin",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "سیاست اقتصادی": ("fed", "rate", "inflation", "economy", "treasury", "policy", "gdp", "employment", "tariff"),
    "زیرساخت AI": ("ai", "artificial intelligence", "gpu", "data center", "openai", "meta", "nvidia", "chip"),
    "سرمایه‌گذاری AI": ("semiconductor", "micron", "memory", "ai investment", "tech valuation", "capital return"),
    "تنش بین‌المللی": ("war", "sanction", "geopolit", "conflict", "military", "strait", "trade route", "tension"),
    "بیت‌کوین": ("bitcoin", "btc", "crypto", "etf", "halving", "mining"),
}


@dataclass
class NewsItem:
    category: str
    title: str
    summary: str


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _categorize(title: str, summary: str) -> str:
    blob = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in blob for k in keywords):
            return category
    return "بازار کریپتو"


def _parse_rss(xml_text: str, limit: int) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for item in root.iter("item"):
        title = _strip_html(item.findtext("title", ""))
        desc = _strip_html(item.findtext("description", ""))
        if title:
            items.append((title, desc[:280]))
        if len(items) >= limit:
            break
    return items


def fetch_btc_news(limit: int = 4) -> list[NewsItem]:
    """Fetch recent BTC/crypto headlines from public RSS feeds."""
    seen: set[str] = set()
    out: list[NewsItem] = []

    for url in RSS_FEEDS:
        try:
            resp = requests.get(url, timeout=12, headers={"User-Agent": "AnalysisOnTel/1.0"})
            resp.raise_for_status()
            for title, summary in _parse_rss(resp.text, limit):
                key = title.lower()[:80]
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    NewsItem(
                        category=_categorize(title, summary),
                        title=title,
                        summary=summary or "—",
                    )
                )
                if len(out) >= limit:
                    return out
        except Exception:
            logger.warning("RSS fetch failed: %s", url)

    if not out:
        out.append(
            NewsItem(
                category="اطلاع‌رسانی",
                title="فید خبری در دسترس نیست",
                summary="تمرکز روی داده‌های مشتقات، تقویم ماکرو و تحلیل تکنیکال.",
            )
        )
    return out
