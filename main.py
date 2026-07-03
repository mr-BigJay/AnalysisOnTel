"""AnalysisOnTel — entry point."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="AnalysisOnTel BTC market report bot")
    parser.add_argument(
        "command",
        choices=["report", "bot", "bot-scheduled"],
        help="report=print once | bot=telegram polling | bot-scheduled=bot + candle alerts",
    )
    args = parser.parse_args()

    if args.command == "report":
        from report.engine import generate_report

        _, text = generate_report()
        # Strip HTML for terminal
        import re

        plain = re.sub(r"<[^>]+>", "", text)
        print(plain)
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
