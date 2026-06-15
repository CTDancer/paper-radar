from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from paper_radar.models import Paper
from paper_radar.utils.dates import utc_now_iso


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                canonical_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                data_json TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                last_shown TEXT
            )
            """
        )
        conn.commit()


def save_papers(path: Path, papers: list[Paper], report_date: str | None = None) -> None:
    init_db(path)
    now = utc_now_iso()
    with sqlite3.connect(path) as conn:
        for paper in papers:
            key = paper.canonical_key()
            existing = conn.execute(
                "SELECT first_seen, last_shown FROM papers WHERE canonical_key = ?", (key,)
            ).fetchone()
            first_seen = existing[0] if existing else now
            last_shown = report_date if report_date else (existing[1] if existing else None)
            conn.execute(
                """
                INSERT OR REPLACE INTO papers
                (canonical_key, title, data_json, first_seen, last_seen, last_shown)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key, paper.title, json.dumps(paper.to_dict()), first_seen, now, last_shown),
            )
        conn.commit()


def load_seen(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def update_seen(path: Path, papers: list[Paper], report_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = load_seen(path)
    now = utc_now_iso()
    for paper in papers:
        key = paper.canonical_key()
        entry = seen.setdefault(key, {"first_seen": now})
        entry["title"] = paper.title
        entry["last_seen"] = now
        entry["last_shown"] = report_date
    path.write_text(json.dumps(seen, indent=2, sort_keys=True), encoding="utf-8")
