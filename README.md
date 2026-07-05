# AnalysisOnTel — BTC Notification Bot

Telegram bot for **BTC-only alerts** (Levels 1–3). No reports, backtest, or multi-coin scan.

## Alerts (automatic in `bot-scheduled` mode)

### Level 1
- RSI oversold / overbought (cross, closed candle) — 1m, 5m, 15m, 1h, 4h
- RSI divergence — 1m, 5m, 15m, 1h, 4h
- Key level break — 1h, 4h

### Level 2
- Liquidity Grab — 15m, 1h
- MSS (Market Structure Shift) — 15m, 1h
- Breakout + Retest entry zone hit — 1h, 4h

### Level 3
- Macro events (USD/EUR high-impact)
- Extreme Fear & Greed
- Extreme funding rate
- Volume spike — 1h, 4h

### Manual (menu)
- **📡 وضعیت** — trend on 1m / 5m / 15m / 1h / 4h
- **🌐 بازار** — Funding, Fear&Greed, L/S, OI, macro with Persian interpretation
- **📊 تکنیکال** — full Technical Analysis report (separate from alerts)
- **📋 گزارش** — comprehensive 4-hour briefing (news + TA + ICT scenarios)

**📋 گزارش ۴H** (automatic every 4 hours in `bot-scheduled`):
- Headline + multi-timeframe trend summary
- Market news (RSS) + macro calendar
- Long-term TA (1D) + short-term TA (1H/4H)
- ICT/SMC: BSL/SSL liquidity, two scenarios with Entry/SL/TP
- Strategy tips + pending limit orders suggestion
- Momentum comparison vs previous report

**📊 تکنیکال** covers:
- Trend (1D / 4H / 1H), support & resistance, price action
- Classic patterns, candlestick (1H), volume
- Indicators: RSI, MACD, EMA, SMA, VWAP, Bollinger, ATR, ADX, Stoch RSI, SuperTrend, Ichimoku, Parabolic SAR

## Commands

```bash
python main.py bot              # Telegram only
python main.py bot-scheduled    # Telegram + auto alerts
python main.py status           # terminal status
python main.py market           # terminal market context
python main.py technical        # terminal TA report
python main.py briefing         # terminal 4H briefing
python main.py scan             # one notification scan
```

Telegram: `/start` `/status` `/market` `/technical` `/briefing` — menu: **وضعیت** | **بازار** | **تکنیکال** | **گزارش** | **راهنما**

## Server install / update

```bash
cd /opt/analysisontel
sudo git fetch origin
sudo git checkout cursor/btc-notif-bot-8654
sudo git pull origin cursor/btc-notif-bot-8654
sudo ./venv/bin/pip install -r requirements.txt
sudo chown -R analysisontel:analysisontel /opt/analysisontel/data
sudo systemctl restart analysisontel
```

## Clean old data (after rewrite)

Remove files from the **previous** bot version:

```bash
sudo systemctl stop analysisontel

sudo rm -f /opt/analysisontel/data/predictions.db
sudo rm -f /opt/analysisontel/data/last_report.json
sudo rm -f /opt/analysisontel/data/active_scenario.json
sudo rm -f /opt/analysisontel/data/rsi_alerts_state.json
sudo rm -f /opt/analysisontel/data/backtest_last.json
sudo rm -f /opt/analysisontel/data/tuning_params.json

# New bot uses only:
# /opt/analysisontel/data/notifications_state.json
# /opt/analysisontel/data/briefing_state.json

sudo chown -R analysisontel:analysisontel /opt/analysisontel/data
sudo systemctl start analysisontel
sudo journalctl -u analysisontel -f
```

Optional — full reinstall:

```bash
sudo systemctl stop analysisontel
sudo rm -rf /opt/analysisontel
sudo bash /path/to/deploy/install.sh   # BRANCH=cursor/btc-notif-bot-8654
sudo nano /etc/analysisontel.env       # token + chat id
sudo systemctl enable --now analysisontel
```

## Config (`/etc/analysisontel.env`)

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_IDS=123456789
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
SCAN_INTERVAL_MINUTES=2
```

## Requirements

- Ubuntu 24, outbound HTTPS only (Telegram polling)
- No inbound ports
