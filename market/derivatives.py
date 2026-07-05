"""Derivatives and sentiment from public APIs."""

from __future__ import annotations

from dataclasses import dataclass

import requests

OKX_FUNDING = "https://www.okx.com/api/v5/public/funding-rate"
OKX_OI = "https://www.okx.com/api/v5/public/open-interest"
OKX_LS = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio"
FNG_URL = "https://api.alternative.me/fng/"


@dataclass
class DerivativesSnapshot:
    funding_rate: float | None
    open_interest_usd: float | None
    long_short_ratio: float | None
    fear_greed_value: int | None
    fear_greed_label: str | None


def _okx(url: str, params: dict) -> dict | None:
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        p = r.json()
        return p if p.get("code") == "0" else None
    except Exception:
        return None


def fetch_derivatives() -> DerivativesSnapshot:
    funding = oi = ls = None
    fng_val = fng_label = None

    fd = _okx(OKX_FUNDING, {"instId": "BTC-USDT-SWAP"})
    if fd and fd.get("data"):
        funding = float(fd["data"][0]["fundingRate"])

    od = _okx(OKX_OI, {"instId": "BTC-USDT-SWAP"})
    if od and od.get("data"):
        oi = float(od["data"][0]["oiUsd"])

    ld = _okx(OKX_LS, {"ccy": "BTC", "period": "1D"})
    if ld and ld.get("data"):
        ls = float(ld["data"][0][1])

    try:
        fng = requests.get(FNG_URL, params={"limit": 1}, timeout=15).json()["data"][0]
        fng_val = int(fng["value"])
        fng_label = str(fng["value_classification"])
    except Exception:
        pass

    return DerivativesSnapshot(funding, oi, ls, fng_val, fng_label)
