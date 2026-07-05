"""Derivatives and sentiment data from public APIs."""

from __future__ import annotations

from dataclasses import dataclass

import requests

OKX_FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate"
OKX_OI_URL = "https://www.okx.com/api/v5/public/open-interest"
OKX_LS_URL = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio"
FNG_URL = "https://api.alternative.me/fng/"


@dataclass
class DerivativesSnapshot:
    funding_rate: float | None
    open_interest_usd: float | None
    long_short_ratio: float | None
    fear_greed_value: int | None
    fear_greed_label: str | None
    source_notes: list[str]

    @property
    def available(self) -> bool:
        return any(
            v is not None
            for v in (self.funding_rate, self.open_interest_usd, self.long_short_ratio, self.fear_greed_value)
        )


def _okx_get(url: str, params: dict) -> dict | None:
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != "0":
            return None
        return payload
    except Exception:
        return None


def fetch_derivatives() -> DerivativesSnapshot:
    notes: list[str] = []
    funding: float | None = None
    oi_usd: float | None = None
    ls_ratio: float | None = None
    fng_val: int | None = None
    fng_label: str | None = None

    funding_data = _okx_get(OKX_FUNDING_URL, {"instId": "BTC-USDT-SWAP"})
    if funding_data and funding_data.get("data"):
        funding = float(funding_data["data"][0]["fundingRate"])
        notes.append("Funding: OKX")
    else:
        notes.append("Funding: unavailable")

    oi_data = _okx_get(OKX_OI_URL, {"instId": "BTC-USDT-SWAP"})
    if oi_data and oi_data.get("data"):
        oi_usd = float(oi_data["data"][0]["oiUsd"])
        notes.append("OI: OKX")
    else:
        notes.append("OI: unavailable")

    ls_data = _okx_get(OKX_LS_URL, {"ccy": "BTC", "period": "1D"})
    if ls_data and ls_data.get("data"):
        # latest row: [timestamp, ratio]
        ls_ratio = float(ls_data["data"][0][1])
        notes.append("L/S: OKX")
    else:
        notes.append("L/S: unavailable")

    try:
        fng_resp = requests.get(FNG_URL, params={"limit": 1}, timeout=15)
        fng_resp.raise_for_status()
        fng = fng_resp.json()["data"][0]
        fng_val = int(fng["value"])
        fng_label = str(fng["value_classification"])
        notes.append("Fear&Greed: alternative.me")
    except Exception:
        notes.append("Fear&Greed: unavailable")

    return DerivativesSnapshot(
        funding_rate=funding,
        open_interest_usd=oi_usd,
        long_short_ratio=ls_ratio,
        fear_greed_value=fng_val,
        fear_greed_label=fng_label,
        source_notes=notes,
    )
