from __future__ import annotations

from pathlib import Path

from paper_radar.config import REPO_ROOT


def run_weekly(start: str, end: str, repo_root: Path = REPO_ROOT) -> Path:
    reports_dir = repo_root / "reports"
    out = reports_dir / f"weekly-{start}-to-{end}.md"
    reports_dir.mkdir(parents=True, exist_ok=True)
    daily_reports = sorted(reports_dir.glob("20*.md"))
    lines = [
        f"# Weekly Paper Radar — {start} to {end}",
        "",
        "This first implementation includes a weekly command placeholder.",
        "",
        "## TODO",
        "",
        "- Load selected papers from the daily reports or SQLite store.",
        "- Summarize the most important papers of the week.",
        "- Identify emerging themes, new methods, advisor-discussion candidates, and related-work additions.",
        "",
        f"Daily reports currently available: {len(daily_reports)}",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
