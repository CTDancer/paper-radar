from __future__ import annotations

import urllib.parse

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher


class DBLPEnricher(SourceFetcher):
    name = "dblp"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        return []

    def enrich(self, papers: list[Paper]) -> list[Paper]:
        for paper in papers:
            if not paper.title:
                continue
            params = urllib.parse.urlencode({"q": paper.title, "format": "json", "h": 1})
            data = self.get_json(f"https://dblp.org/search/publ/api?{params}")
            if not data:
                if self.should_stop():
                    break
                continue
            hits = data.get("result", {}).get("hits", {}).get("hit", [])
            if not hits:
                continue
            info = hits[0].get("info", {})
            if info.get("venue") and not paper.venue:
                paper.venue = info["venue"]
            if info.get("url"):
                paper.source_links.setdefault(self.name, info["url"])
        return papers
