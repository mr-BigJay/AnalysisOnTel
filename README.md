# AnalysisOnTel v2 — Institutional BTC Web Dashboard

Web-based institutional BTC analysis engine. **No Telegram bot.**

## Framework

Analysis priority (institutional):
1. **Market Structure** — HH/HL/LH/LL, BOS, MSS, CHoCH
2. **Liquidity** — BSL, SSL, equal highs/lows, sweeps
3. **ICT** — Order Blocks, FVG, Premium/Discount, OTE, Kill Zones
4. **Wyckoff** — Accumulation, Distribution, Spring, Upthrust
5. **Order Flow** — Volume, OI, Funding, L/S positioning
6. **Macro** — Calendar, news, Fear & Greed

RSI/MACD/MA are **not** primary signals — only supporting context.

## Decision engine

- Bull/Bear probability (never 50/50)
- 8 confirmation checks — need **5+ core** for trade
- Verdict: `LONG` | `SHORT` | `WAIT` | `NO TRADE`
- Trade plan: Entry, SL, TP1-3, R:R, leverage cap

## Quick start (local)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open **http://localhost:9443**

## Server install (fresh Ubuntu)

```bash
sudo BRANCH=cursor/web-dashboard-8654 bash deploy/install.sh
sudo nano /etc/analysisontel.env   # set WEB_PASSWORD
sudo systemctl enable --now analysisontel
```

Dashboard: `http://YOUR_SERVER_IP:9443`  
Login: `admin` / your `WEB_PASSWORD`

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/report` | GET | Latest JSON report |
| `/api/report/refresh` | POST | Force re-analysis |
| `/api/health` | GET | Health check |

## Config (`/etc/analysisontel.env`)

```
WEB_HOST=0.0.0.0
WEB_PORT=9443
WEB_PASSWORD=your_password
REFRESH_INTERVAL_MINUTES=240
```

## Data sources

- OHLCV: Kraken (BTC/USD)
- Funding, OI, L/S: OKX
- Fear & Greed: alternative.me
- Macro calendar: ForexFactory JSON
- News: CoinTelegraph / CoinDesk RSS

## Firewall

```bash
sudo ufw allow 9443/tcp
```

For production, put nginx + HTTPS in front.

## Disclaimer

Informational analysis only. Not financial advice. Max 1% risk / 20x leverage enforced in recommendations.
