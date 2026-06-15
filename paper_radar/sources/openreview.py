from __future__ import annotations

import urllib.parse
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.dates import within_lookback
from paper_radar.utils.urls import find_code_url


class OpenReviewFetcher(SourceFetcher):
    name = "openreview"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        for query in query_groups:
            params = urllib.parse.urlencode({"term": query, "limit": per_query})
            data = self.get_json(f"https://api2.openreview.net/notes/search?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            for item in data.get("notes", []) or data.get("results", []):
                paper = self._paper_from_item(item, lookback_days)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any], lookback_days: int) -> Paper | None:
        content = item.get("content", {})
        title = value(content.get("title")) or item.get("forum", "")
        if not title:
            return None
        date = ""
        cdate = item.get("cdate") or item.get("tcdate")
        if cdate:
            from datetime import datetime

            date = datetime.utcfromtimestamp(cdate / 1000).date().isoformat()
        if date and not within_lookback(date, lookback_days):
            return None
        abstract = value(content.get("abstract"))
        authors = value(content.get("authors"))
        if isinstance(authors, str):
            authors = [authors]
        url = f"https://openreview.net/forum?id={item.get('forum') or item.get('id')}"
        return Paper(
            title=title,
            authors=authors or [],
            abstract=abstract,
            source=self.name,
            date=date,
            venue=value(content.get("venue")) or item.get("domain", ""),
            url=url,
            openalex_id="",
            code_url=find_code_url(f"{title} {abstract}"),
            publication_type="preprint",
        )


def value(raw: Any) -> Any:
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw or ""
