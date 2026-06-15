from __future__ import annotations

import urllib.parse

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher


class PapersWithCodeEnricher(SourceFetcher):
    name = "papers_with_code"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        return []

    def enrich(self, papers: list[Paper]) -> list[Paper]:
        for paper in papers:
            if paper.code_url:
                continue
            params = urllib.parse.urlencode({"q": paper.title})
            data = self.get_json(f"https://paperswithcode.com/api/v1/papers/?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            results = data.get("results", [])
            if not results:
                continue
            match = results[0]
            paper.source_links.setdefault(self.name, match.get("url_abs") or match.get("url", ""))
            repo_url = first_repository_url(match)
            if repo_url:
                paper.code_url = repo_url
        return papers


def first_repository_url(match: dict) -> str:
    repos = match.get("repositories") or []
    if repos and isinstance(repos[0], dict):
        return repos[0].get("url") or ""
    return ""
