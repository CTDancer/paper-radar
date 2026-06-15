from __future__ import annotations

import urllib.parse
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.dates import within_lookback
from paper_radar.utils.urls import find_code_url


class ChemRxivFetcher(SourceFetcher):
    name = "chemrxiv"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        for query in query_groups:
            params = urllib.parse.urlencode({"term": query, "limit": per_query, "skip": 0})
            data = self.get_json(f"https://chemrxiv.org/engage/chemrxiv/public-api/v1/items?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            items = data.get("itemHits") or data.get("items") or []
            for hit in items:
                item = hit.get("item", hit) if isinstance(hit, dict) else {}
                paper = self._paper_from_item(item, lookback_days)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any], lookback_days: int) -> Paper | None:
        title = item.get("title") or item.get("name") or ""
        if not title:
            return None
        date = (item.get("publishedDate") or item.get("postedDate") or item.get("createdDate") or "")[:10]
        if not within_lookback(date, lookback_days):
            return None
        abstract = item.get("abstract") or item.get("description") or ""
        authors = []
        for author in item.get("authors", []) or []:
            if isinstance(author, dict):
                full = author.get("fullName") or " ".join([author.get("firstName", ""), author.get("lastName", "")]).strip()
                if full:
                    authors.append(full)
        doi = item.get("doi") or ""
        url = item.get("url") or item.get("assetUrl") or (f"https://doi.org/{doi}" if doi else "")
        return Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            source=self.name,
            date=date,
            venue="ChemRxiv",
            doi=doi,
            url=url,
            pdf_url=item.get("pdfUrl", ""),
            code_url=find_code_url(f"{title} {abstract}"),
            publication_type="preprint",
        )
