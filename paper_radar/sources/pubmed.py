from __future__ import annotations

import os
import urllib.parse
import xml.etree.ElementTree as ET

from paper_radar.models import Paper
from paper_radar.sources.base import SourceFetcher
from paper_radar.utils.urls import find_code_url


class PubMedFetcher(SourceFetcher):
    name = "pubmed"

    def fetch(self, query_groups: list[str], lookback_days: int) -> list[Paper]:
        papers: list[Paper] = []
        per_query = max(5, self.max_results // max(1, len(query_groups)))
        for query in query_groups:
            ids = self._search(query, lookback_days, per_query)
            if ids:
                papers.extend(self._fetch_details(ids))
        return papers

    def _common_params(self) -> dict[str, str]:
        params: dict[str, str] = {"tool": "paper-radar"}
        if os.getenv("NCBI_EMAIL"):
            params["email"] = os.environ["NCBI_EMAIL"]
        if os.getenv("NCBI_API_KEY"):
            params["api_key"] = os.environ["NCBI_API_KEY"]
        return params

    def _search(self, query: str, lookback_days: int, limit: int) -> list[str]:
        params = {
            **self._common_params(),
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(limit),
            "sort": "pub date",
            "datetype": "pdat",
            "reldate": str(max(1, lookback_days)),
        }
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{urllib.parse.urlencode(params)}"
        data = self.get_json(url)
        return data.get("esearchresult", {}).get("idlist", [])

    def _fetch_details(self, ids: list[str]) -> list[Paper]:
        params = {**self._common_params(), "db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{urllib.parse.urlencode(params)}"
        text = self.get_text(url)
        if not text:
            return []
        root = ET.fromstring(text)
        papers: list[Paper] = []
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue
            pmid = medline.findtext("PMID", default="")
            article_node = medline.find("Article")
            if article_node is None:
                continue
            title = " ".join(article_node.findtext("ArticleTitle", default="").split())
            if not title:
                continue
            abstract = " ".join(
                text_node.text or "" for text_node in article_node.findall(".//AbstractText")
            )
            authors = []
            for author in article_node.findall(".//Author"):
                last = author.findtext("LastName", default="")
                fore = author.findtext("ForeName", default="")
                full = " ".join([fore, last]).strip()
                if full:
                    authors.append(full)
            journal = article_node.findtext(".//Journal/Title", default="")
            year = article_node.findtext(".//PubDate/Year", default="")
            month = article_node.findtext(".//PubDate/Month", default="01")
            day = article_node.findtext(".//PubDate/Day", default="01")
            date = normalize_pubmed_date(year, month, day)
            doi = ""
            for article_id in article.findall(".//ArticleId"):
                if article_id.attrib.get("IdType") == "doi":
                    doi = article_id.text or ""
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            papers.append(
                Paper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    source=self.name,
                    date=date,
                    venue=journal,
                    doi=doi,
                    pubmed_id=pmid,
                    url=url,
                    code_url=find_code_url(f"{title} {abstract}"),
                    publication_type="journal article",
                )
            )
        return papers


def normalize_pubmed_date(year: str, month: str, day: str) -> str:
    months = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    if not year:
        return ""
    mm = months.get(month[:3].lower(), month if month.isdigit() else "01").zfill(2)
    dd = day if day.isdigit() else "01"
    return f"{year}-{mm}-{dd.zfill(2)}"
