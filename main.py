"""AnalysisOnTel — BTC notification bot."""

from __future__ import annotations

import argparse
import re
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="AnalysisOnTel BTC notification bot")
    parser.add_argument(
        "command",
        choices=["scan", "status", "bot", "bot-scheduled"],
        help="scan | status | bot | bot-scheduled",
    )
    args = parser.parse_args()

    if args.command == "scan":
        from notifications.engine import run_btc_notifications

        for msg in run_btc_notifications():
            print(re.sub(r"<[^>]+>", "", msg))
            print("-" * 40)
        return

    if args.command == "status":
        from bot.status_format import format_status_report
        from market.status import fetch_market_status

        print(re.sub(r"<[^>]+>", "", format_status_report(fetch_market_status())))
        return

    if args.command in ("bot", "bot-scheduled"):
        if args.command == "bot-scheduled":
            from bot.scheduler import start_scheduler

            start_scheduler()
        from bot.telegram_bot import run_bot

        run_bot()
        return

    sys.exit(1)


if __name__ == "__main__":
    main()
