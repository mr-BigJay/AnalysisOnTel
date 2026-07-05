"""Macro context and news."""

from __future__ import annotations

from dataclasses import dataclass

from market.derivatives import DerivativesSnapshot
from market.events import get_upcoming_events
from market.news import fetch_headlines


@dataclass
class MacroAnalysis:
    events: list[dict]
    headlines: list[dict]
    sentiment: str
    summary: str
    risky: bool
    bullish: bool
    bearish: bool


def analyze_macro(deriv: DerivativesSnapshot) -> MacroAnalysis:
    events = get_upcoming_events(48)
    headlines = fetch_headlines(5)
    risky = any(e["impact"] == "High" for e in events)

    if deriv.fear_greed_value is not None:
        v = deriv.fear_greed_value
        if v <= 25:
            sentiment = f"Extreme Fear ({v}) — contrarian bullish context"
            bull, bear = True, False
        elif v >= 75:
            sentiment = f"Extreme Greed ({v}) — contrarian bearish context"
            bull, bear = False, True
        elif v < 45:
            sentiment = f"Fear ({v}) — cautious"
            bull, bear = False, True
        elif v > 55:
            sentiment = f"Greed ({v}) — risk-on"
            bull, bear = True, False
        else:
            sentiment = f"Neutral ({v})"
            bull = bear = False
    else:
        sentiment = "Sentiment unavailable"
        bull = bear = False

    summary = sentiment
    if events:
        summary += f" | {len(events)} macro events in 48h"
        if risky:
            summary += " (HIGH impact near)"
    if headlines:
        summary += f" | Top headline: {headlines[0]['title'][:80]}"

    return MacroAnalysis(events, headlines, sentiment, summary, risky, bull, bear)


def macro_dict(m: MacroAnalysis) -> dict:
    return {
        "events": m.events,
        "headlines": m.headlines,
        "sentiment": m.sentiment,
        "summary": m.summary,
        "risky": m.risky,
    }
