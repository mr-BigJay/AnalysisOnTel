"""AnalysisOnTel — entry point."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="AnalysisOnTel BTC market report bot")
    parser.add_argument(
        "command",
        choices=["report", "stats", "review", "backtest", "bot", "bot-scheduled"],
        help="report | stats | review | backtest | bot | bot-scheduled",
    )
    args = parser.parse_args()

    if args.command == "report":
        from report.engine import generate_report_messages

        _, messages = generate_report_messages()
        import re

        for msg in messages:
            plain = re.sub(r"<[^>]+>", "", msg)
            print(plain)
            print("-" * 40)
        return

    if args.command == "stats":
        from tracking.stats import format_stats_report
        import re

        print(re.sub(r"<[^>]+>", "", format_stats_report()))
        return

    if args.command == "review":
        from tracking.review import format_review_report
        import re

        print(re.sub(r"<[^>]+>", "", format_review_report()))
        return

    if args.command == "backtest":
        from backtest.report import run_and_format
        import re

        print(re.sub(r"<[^>]+>", "", run_and_format()))
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
