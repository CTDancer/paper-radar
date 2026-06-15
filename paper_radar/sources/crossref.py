from __future__ import annotations

import urllib.parse
from datetime import date, timedelta
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.urls import find_code_url


class CrossrefFetcher(SourceFetcher):
    name = "crossref"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        from_date = (date.today() - timedelta(days=lookback_days)).isoformat()
        for query in query_groups:
            params = urllib.parse.urlencode(
                {
                    "query": query,
                    "rows": per_query,
                    "sort": "published",
                    "order": "desc",
                    "filter": f"from-pub-date:{from_date}",
                }
            )
            data = self.get_json(f"https://api.crossref.org/works?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            for item in data.get("message", {}).get("items", []):
                paper = self._paper_from_item(item)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any]) -> Paper | None:
        title = " ".join(item.get("title") or []).strip()
        if not title:
            return None
        abstract = strip_jats(item.get("abstract", ""))
        authors = []
        for author in item.get("author", [])[:20]:
            full = " ".join([author.get("given", ""), author.get("family", "")]).strip()
            if full:
                authors.append(full)
        date_parts = (
            item.get("published-print", {})
            or item.get("published-online", {})
            or item.get("created", {})
        ).get("date-parts", [[]])[0]
        pub_date = "-".join(str(part).zfill(2) for part in date_parts[:3]) if date_parts else ""
        doi = item.get("DOI", "")
        url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        return Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            source=self.name,
            date=pub_date,
            venue=" ".join(item.get("container-title") or []),
            doi=doi,
            url=url,
            code_url=find_code_url(f"{title} {abstract}"),
            citation_count=item.get("is-referenced-by-count"),
            publication_type=item.get("type", ""),
        )


def strip_jats(text: str) -> str:
    out = []
    in_tag = False
    for ch in text or "":
        if ch == "<":
            in_tag = True
            out.append(" ")
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    return " ".join("".join(out).split())
