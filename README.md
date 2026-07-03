# AnalysisOnTel

ربات گزارش بازار BTC برای تلگرام — تحلیل چندتایم‌فریمی (روزانه + ۴H + ۱H).

## ویژگی‌ها

- گزارش فارسی ساده و واضح با دستور `/report` یا `/گزارش`
- جهت روزانه تعیین‌کننده — خلاف روند بلندمدت = پرریسک
- سناریو ورود شرطی: «اگر قیمت به X رسید → لانگ/شورت»
- امتیاز کیفیت ۰–۱۰۰
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
| `/گزارش` | همان گزارش |

## منبع داده

Kraken Public API — BTC/USD

## تولید چارت (اختیاری)

```bash
python3 chart_btc.py
```
