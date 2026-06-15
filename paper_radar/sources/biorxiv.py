from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.text import contains_any
from paper_radar.utils.urls import find_code_url


class BioRxivFetcher(SourceFetcher):
    name = "biorxiv"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        server = self.settings.get("server", "biorxiv")
        end = date.today()
        start = end - timedelta(days=lookback_days)
        papers: list[Paper] = []
        cursor = 0
        terms = query_terms(query_groups)
        while len(papers) < self.max_results and not self.should_stop():
            url = f"https://api.biorxiv.org/details/{server}/{start.isoformat()}/{end.isoformat()}/{cursor}"
            data = self.get_json(url)
            if not data:
                break
            collection = data.get("collection", [])
            if not collection:
                break
            for item in collection:
                title = item.get("title", "")
                abstract = item.get("abstract", "")
                if terms and not contains_any(f"{title} {abstract}", terms):
                    continue
                papers.append(
                    Paper(
                        title=title,
                        authors=[a.strip() for a in (item.get("authors") or "").split(";") if a.strip()],
                        abstract=abstract,
                        source=self.name,
                        date=item.get("date", ""),
                        venue=server,
                        doi=item.get("doi", ""),
                        url=item.get("url", ""),
                        pdf_url=item.get("jatsxml", ""),
                        code_url=find_code_url(f"{title} {abstract}"),
                        publication_type="preprint",
                    )
                )
                if len(papers) >= self.max_results:
                    break
            cursor += len(collection)
        return papers


def query_terms(query_groups: list[str]) -> list[str]:
    terms: list[str] = []
    for group in query_groups:
        terms.extend([part for part in group.split() if len(part) > 4])
    return sorted(set(terms))
