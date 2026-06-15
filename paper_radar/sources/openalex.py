from __future__ import annotations

import urllib.parse
from datetime import date, timedelta
from html import unescape
import re
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.urls import find_code_url


class OpenAlexFetcher(SourceFetcher):
    name = "openalex"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        from_date = (date.today() - timedelta(days=lookback_days)).isoformat()
        for query in query_groups:
            params = urllib.parse.urlencode(
                {
                    "search": query,
                    "per-page": per_query,
                    "filter": f"from_publication_date:{from_date}",
                    "sort": "publication_date:desc",
                }
            )
            data = self.get_json(f"https://api.openalex.org/works?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            for item in data.get("results", []):
                paper = self._paper_from_item(item)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any]) -> Paper | None:
        title = clean_markup(item.get("title") or item.get("display_name") or "")
        if not title:
            return None
        authors = [
            auth.get("author", {}).get("display_name", "")
            for auth in item.get("authorships", [])
            if auth.get("author", {}).get("display_name")
        ]
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        abstract = clean_markup(reconstruct_abstract(item.get("abstract_inverted_index") or {}))
        primary = item.get("primary_location") or {}
        landing = primary.get("landing_page_url") or item.get("id") or ""
        pdf_url = primary.get("pdf_url") or ""
        code_url = find_code_url(f"{title} {abstract}")
        fields = [concept.get("display_name", "") for concept in item.get("concepts", [])[:8]]
        return Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            source=self.name,
            date=item.get("publication_date") or "",
            venue=(primary.get("source") or {}).get("display_name", ""),
            doi=doi,
            openalex_id=item.get("id", ""),
            url=landing,
            pdf_url=pdf_url,
            code_url=code_url,
            citation_count=item.get("cited_by_count"),
            fields_of_study=[f for f in fields if f],
            publication_type=item.get("type", ""),
        )


def reconstruct_abstract(index: dict[str, list[int]]) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, locs in index.items():
        for loc in locs:
            positions.append((loc, word))
    return " ".join(word for _, word in sorted(positions))


def clean_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(text or "")).strip()
