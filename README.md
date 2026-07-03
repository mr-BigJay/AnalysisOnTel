# AnalysisOnTel

ربات گزارش بازار BTC برای تلگرام — تحلیل چندتایم‌فریمی (روزانه + ۴H + ۱H).

## ویژگی‌ها (نسخه پیشرفته)

- گزارش فارسی ساده و واضح با دستور `/report` یا `/gozaresh`
- جهت روزانه تعیین‌کننده — خلاف روند بلندمدت = پرریسک
- سناریو ورود شرطی: «اگر قیمت به X رسید → لانگ/شورت»
- **چک‌لیست ۱۰ مرحله‌ای کیفیت** قبل از هر سیگنال
- **Funding Rate + Open Interest + Long/Short** از OKX
- **شاخص ترس و طمع** از alternative.me
- امتیاز کیفیت ۰–۱۰۰ (ورود فقط ≥ ۷۰)
- هشدار خودکار با بسته شدن کندل (اختیاری)

## نصب

```bash
pip install -r requirements.txt
```

## تنظیمات

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token-from-BotFather"
export TELEGRAM_CHAT_IDS="123456789"   # اختیاری — برای هشدار خودکار
```

## اجرا

```bash
# یک‌بار گزارش در ترمینال
python3 main.py report

# ربات تلگرام (فقط با دستور کاربر)
python3 main.py bot

# ربات + هشدار بسته شدن کندل
python3 main.py bot-scheduled
```

## دستورات تلگرام

| دستور | عمل |
|--------|-----|
| `/start` | راهنما |
| `/report` | گزارش کامل لحظه‌ای |
| `/gozaresh` | همان گزارش |
| `گزارش` | همان گزارش (متن ساده، بدون /) |
| `/stats` | آمار Win Rate و عملکرد |

## مرحله ۳ — ثبت پیش‌بینی

- هر گزارش با bias مشخص در SQLite ذخیره می‌شود (`data/predictions.db`)
- بعد از ۴ ساعت نتیجه خودکار ارزیابی می‌شود (برد/باخت/نامشخص)
- `/stats` آمار ۷ روز، ۳۰ روز و کل دوره را نشان می‌دهد

## منبع داده

Kraken Public API — BTC/USD

## تولید چارت (اختیاری)

```bash
python3 chart_btc.py
```

## استقرار روی Ubuntu 24.04 (سرور)

این ربات از **Telegram Polling** استفاده می‌کند — فقط اتصال **خروجی** به تلگرام دارد.
**هیچ پورتی (۸۰، ۴۴۳، ۸۰۸۰، …) باز نمی‌کند.**

```bash
# روی سرور — با root یا sudo
sudo bash deploy/install.sh
sudo nano /etc/analysisontel.env   # توکن و Chat ID
sudo systemctl enable --now analysisontel
sudo journalctl -u analysisontel -f
```
