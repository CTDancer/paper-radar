from __future__ import annotations

import argparse
from pathlib import Path

from paper_radar.config import REPO_ROOT, load_all_configs
from paper_radar.logging_utils import configure_logging
from paper_radar.pipeline.candidates import run_daily_candidates
from paper_radar.pipeline.run_daily import run_daily, run_fetch_only
from paper_radar.pipeline.weekly import run_weekly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-radar", description="Daily research paper radar")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch and store recent candidates")
    fetch.add_argument("--lookback-days", type=int, default=3)

    rank = subparsers.add_parser("rank", help="Placeholder: ranking is run as part of daily")
    rank.add_argument("--date", required=True)

    summarize = subparsers.add_parser("summarize", help="Placeholder: summarization is run as part of daily")
    summarize.add_argument("--date", required=True)
    summarize.add_argument("--top-k", type=int, default=10)

    daily = subparsers.add_parser("daily", help="Run the API-backed final-report workflow")
    daily.add_argument("--lookback-days", type=int, default=3)
    daily.add_argument("--top-k", type=int, default=10)
    daily.add_argument("--date", default=None, help="Override report date as YYYY-MM-DD")
    daily.add_argument("--mode", choices=["api"], default="api", help="Only API mode writes final summaries from Python")
    daily.add_argument(
        "--no-llm",
        action="store_true",
        help="Deprecated: use daily-candidates for no-API Codex mode",
    )

    candidates = subparsers.add_parser("daily-candidates", help="Generate rich candidates for Codex-mode report writing")
    candidates.add_argument("--lookback-days", type=int, default=3)
    candidates.add_argument("--top-k", type=int, default=30)
    candidates.add_argument("--date", default=None, help="Override report date as YYYY-MM-DD")

    weekly = subparsers.add_parser("weekly", help="Create a weekly synthesis placeholder")
    weekly.add_argument("--start", required=True)
    weekly.add_argument("--end", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    if args.command == "fetch":
        result = run_fetch_only(lookback_days=args.lookback_days, repo_root=REPO_ROOT)
        print(
            f"Fetched {result['raw']} raw candidates; {result['deduplicated']} remained after deduplication."
        )
        return 0
    if args.command == "daily-candidates":
        json_path, md_path = run_daily_candidates(
            lookback_days=args.lookback_days,
            top_k=args.top_k,
            report_date=args.date,
            repo_root=REPO_ROOT,
        )
        print(f"Wrote candidate JSON: {json_path}")
        print(f"Wrote candidate Markdown: {md_path}")
        return 0
    if args.command == "daily":
        if args.no_llm:
            parser.error("Final no-LLM reports are disabled. Use `daily-candidates` for Codex mode.")
        path = run_daily(
            lookback_days=args.lookback_days,
            top_k=args.top_k,
            report_date=args.date,
            repo_root=REPO_ROOT,
            use_llm=True,
        )
        print(f"Wrote daily report: {path}")
        return 0
    if args.command == "weekly":
        path = run_weekly(args.start, args.end, repo_root=REPO_ROOT)
        print(f"Wrote weekly report: {path}")
        return 0
    if args.command in {"rank", "summarize"}:
        load_all_configs(Path(REPO_ROOT) / "config")
        print(f"`{args.command}` is available as a staged placeholder; use `daily` for the full workflow.")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
