# AnalysisOnTel — BTC Notification Bot

Telegram bot for **BTC-only alerts** (Levels 1–3). No reports, backtest, or multi-coin scan.

## Alerts (automatic in `bot-scheduled` mode)

### Level 1
- RSI oversold / overbought (cross, closed candle) — 5m, 15m, 1h, 4h
- RSI divergence — 5m, 15m, 1h, 4h
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
- **📡 وضعیت** — trend on 5m / 15m / 1h / 4h

## Commands

```bash
python main.py bot              # Telegram only
python main.py bot-scheduled    # Telegram + auto alerts
python main.py status           # terminal status
python main.py scan             # one notification scan
```

Telegram: `/start` `/status` `/vaziat` — menu: **وضعیت** | **راهنما**

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
