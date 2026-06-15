from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.dates import within_lookback
from paper_radar.utils.urls import find_code_url


class ArxivFetcher(SourceFetcher):
    name = "arxiv"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        for query in query_groups:
            search_query = " OR ".join(f'all:"{part.strip()}"' for part in query.split()[:6])
            papers.extend(self._query_arxiv(search_query, per_query, lookback_days))
            if self.should_stop():
                break

        broad = self.settings.get("broad_discovery", {})
        if broad.get("enabled") and not self.should_stop():
            max_broad = int(broad.get("max_results", 40))
            categories = broad.get("categories", [])
            per_category = max(5, max_broad // max(1, len(categories)))
            for category in categories:
                papers.extend(self._query_arxiv(f"cat:{category}", per_category, lookback_days))
                if self.should_stop():
                    break
        return papers

    def _query_arxiv(self, search_query: str, max_results: int, lookback_days: int) -> list[Paper]:
        params = urllib.parse.urlencode(
            {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        text = self.get_text(f"http://export.arxiv.org/api/query?{params}")
        if not text:
            return []
        return self._parse(text, lookback_days)

    def _parse(self, text: str, lookback_days: int) -> list[Paper]:
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        root = ET.fromstring(text)
        papers: list[Paper] = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            abstract = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:10]
            if not within_lookback(published, lookback_days):
                continue
            url = entry.findtext("atom:id", default="", namespaces=ns) or ""
            arxiv_id = url.rsplit("/", 1)[-1]
            authors = [
                (author.findtext("atom:name", default="", namespaces=ns) or "").strip()
                for author in entry.findall("atom:author", ns)
            ]
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href", "")
            doi = entry.findtext("arxiv:doi", default="", namespaces=ns) or ""
            code_url = find_code_url(f"{title} {abstract}")
            papers.append(
                Paper(
                    title=title,
                    authors=[a for a in authors if a],
                    abstract=abstract,
                    source=self.name,
                    date=published,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=url,
                    pdf_url=pdf_url,
                    code_url=code_url,
                    publication_type="preprint",
                )
            )
        return papers
