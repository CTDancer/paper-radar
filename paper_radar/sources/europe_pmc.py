from __future__ import annotations

import urllib.parse
from html import unescape
import re
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.dates import within_lookback
from paper_radar.utils.urls import find_code_url


class EuropePMCFetcher(SourceFetcher):
    name = "europe_pmc"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        for query in query_groups:
            params = urllib.parse.urlencode(
                {
                    "query": query,
                    "format": "json",
                    "pageSize": per_query,
                    "sort": "FIRST_PDATE_D desc",
                }
            )
            data = self.get_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            for item in data.get("resultList", {}).get("result", []):
                paper = self._paper_from_item(item, lookback_days)
                if paper:
                    papers.append(paper)
        return papers

    def _paper_from_item(self, item: dict[str, Any], lookback_days: int) -> Paper | None:
        date = item.get("firstPublicationDate") or item.get("pubYear") or ""
        if not within_lookback(date, lookback_days):
            return None
        title = clean_markup(item.get("title") or "")
        if not title:
            return None
        abstract = clean_markup(item.get("abstractText") or "")
        url = ""
        if item.get("pmid"):
            url = f"https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/"
        elif item.get("doi"):
            url = f"https://doi.org/{item['doi']}"
        elif item.get("id"):
            url = f"https://europepmc.org/article/{item.get('source', 'MED')}/{item['id']}"
        return Paper(
            title=title,
            authors=[a.strip() for a in (item.get("authorString") or "").split(",") if a.strip()],
            abstract=abstract,
            source=self.name,
            date=date[:10],
            venue=item.get("journalTitle") or "",
            doi=item.get("doi") or "",
            pubmed_id=item.get("pmid") or "",
            url=url,
            code_url=find_code_url(f"{title} {abstract}"),
            citation_count=int(item["citedByCount"]) if str(item.get("citedByCount", "")).isdigit() else None,
            publication_type=item.get("pubType") or "",
        )


def clean_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(text or "")).strip()
