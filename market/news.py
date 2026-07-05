"""BTC news headlines."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import requests

FEEDS = [
    "https://cointelegraph.com/rss/tag/bitcoin",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]


def fetch_headlines(limit: int = 6) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for url in FEEDS:
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "AnalysisOnTel/2.0"})
            r.raise_for_status()
            root = ET.fromstring(r.text)
            for item in root.iter("item"):
                title = re.sub(r"<[^>]+>", "", item.findtext("title", "")).strip()
                if not title or title.lower() in seen:
                    continue
                seen.add(title.lower())
                out.append({"title": title, "source": url.split("/")[2]})
                if len(out) >= limit:
                    return out
        except Exception:
            continue
    return out
