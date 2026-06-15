from __future__ import annotations

import os

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher


class UnpaywallEnricher(SourceFetcher):
    name = "unpaywall"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        return []

    def enrich(self, papers: list[Paper]) -> list[Paper]:
        email = os.getenv("UNPAYWALL_EMAIL") or os.getenv("NCBI_EMAIL") or ""
        if not email:
            self._record_error("missing email")
            return papers
        for paper in papers:
            if not paper.doi or paper.pdf_url:
                continue
            data = self.get_json(f"https://api.unpaywall.org/v2/{self.quote(paper.doi)}?email={self.quote(email)}")
            if not data:
                if self.should_stop():
                    break
                continue
            best = data.get("best_oa_location") or {}
            paper.pdf_url = paper.pdf_url or best.get("url_for_pdf") or ""
            if not paper.url:
                paper.url = best.get("url") or data.get("doi_url", "")
            if paper.pdf_url:
                paper.source_links[self.name] = paper.pdf_url
        return papers
