from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def today_iso() -> str:
    return date.today().isoformat()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_date(value: str) -> date | None:
    if not value:
        return None
    value = value[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y %b %d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def within_lookback(value: str, lookback_days: int, today: date | None = None) -> bool:
    parsed = parse_date(value)
    if parsed is None:
        return True
    anchor = today or date.today()
    return anchor - timedelta(days=lookback_days) <= parsed <= anchor


def recency_score(value: str, today: date | None = None) -> float:
    parsed = parse_date(value)
    if parsed is None:
        return 0.2
    days = max(0, ((today or date.today()) - parsed).days)
    if days <= 3:
        return 1.0
    if days <= 14:
        return 0.7
    if days <= 45:
        return 0.4
    return 0.1
