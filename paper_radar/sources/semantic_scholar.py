from __future__ import annotations

import os
import urllib.parse
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.dates import within_lookback
from paper_radar.utils.urls import find_code_url


class SemanticScholarFetcher(SourceFetcher):
    name = "semantic_scholar"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        fields = ",".join(
            [
                "title",
                "authors",
                "abstract",
                "year",
                "publicationDate",
                "venue",
                "externalIds",
                "url",
                "citationCount",
                "fieldsOfStudy",
                "publicationTypes",
                "openAccessPdf",
            ]
        )
        headers = {"User-Agent": "paper-radar/0.1"}
        if os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
            headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
        for query in query_groups:
            params = urllib.parse.urlencode({"query": query, "limit": per_query, "fields": fields})
            data = self.get_json(
                f"https://api.semanticscholar.org/graph/v1/paper/search?{params}",
                headers=headers,
            )
            if not data:
                if self.should_stop():
                    break
                continue
            for item in data.get("data", []):
                paper = self._paper_from_item(item, lookback_days)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any], lookback_days: int) -> Paper | None:
        date = item.get("publicationDate") or str(item.get("year") or "")
        if not within_lookback(date, lookback_days):
            return None
        title = item.get("title") or ""
        if not title:
            return None
        external = item.get("externalIds") or {}
        abstract = item.get("abstract") or ""
        pdf = item.get("openAccessPdf") or {}
        code_url = find_code_url(f"{title} {abstract}")
        return Paper(
            title=title,
            authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
            abstract=abstract,
            source=self.name,
            date=date,
            venue=item.get("venue") or "",
            doi=external.get("DOI", ""),
            arxiv_id=external.get("ArXiv", ""),
            pubmed_id=external.get("PubMed", ""),
            semantic_scholar_id=item.get("paperId", ""),
            url=item.get("url") or "",
            pdf_url=pdf.get("url") or "",
            code_url=code_url,
            citation_count=item.get("citationCount"),
            fields_of_study=item.get("fieldsOfStudy") or [],
            publication_type=", ".join(item.get("publicationTypes") or []),
        )
