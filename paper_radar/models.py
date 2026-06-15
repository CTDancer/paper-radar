from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Paper:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    source: str = ""
    date: str = ""
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    semantic_scholar_id: str = ""
    openalex_id: str = ""
    url: str = ""
    pdf_url: str = ""
    code_url: str = ""
    citation_count: int | None = None
    references: list[str] = field(default_factory=list)
    fields_of_study: list[str] = field(default_factory=list)
    publication_type: str = ""
    fetched_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_links: dict[str, str] = field(default_factory=dict)
    topic_tags: list[str] = field(default_factory=list)
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    priority: str = "Archive"
    summary: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.title = " ".join((self.title or "").split())
        self.abstract = " ".join((self.abstract or "").split())
        if self.source and self.url:
            self.source_links.setdefault(self.source, self.url)

    def identifier_keys(self) -> list[str]:
        keys: list[str] = []
        for prefix, value in (
            ("doi", self.doi),
            ("arxiv", self.arxiv_id),
            ("s2", self.semantic_scholar_id),
            ("pmid", self.pubmed_id),
            ("openalex", self.openalex_id),
        ):
            if value:
                keys.append(f"{prefix}:{value.strip().lower()}")
        return keys

    def canonical_key(self) -> str:
        keys = self.identifier_keys()
        if keys:
            return keys[0]
        return f"title:{self.normalized_title()}"

    def normalized_title(self) -> str:
        return normalize_title(self.title)

    def merge(self, other: "Paper") -> "Paper":
        for field_name in (
            "doi",
            "arxiv_id",
            "pubmed_id",
            "semantic_scholar_id",
            "openalex_id",
            "url",
            "pdf_url",
            "code_url",
            "venue",
            "publication_type",
            "date",
        ):
            if not getattr(self, field_name) and getattr(other, field_name):
                setattr(self, field_name, getattr(other, field_name))

        if len(other.abstract) > len(self.abstract):
            self.abstract = other.abstract
        if len(other.authors) > len(self.authors):
            self.authors = other.authors
        if other.citation_count is not None:
            if self.citation_count is None or other.citation_count > self.citation_count:
                self.citation_count = other.citation_count

        self.references = sorted(set(self.references + other.references))
        self.fields_of_study = sorted(set(self.fields_of_study + other.fields_of_study))
        self.topic_tags = sorted(set(self.topic_tags + other.topic_tags))
        if other.source and other.url:
            self.source_links[other.source] = other.url
        if other.source and other.source not in self.source.split("+"):
            self.source = "+".join([s for s in [self.source, other.source] if s])
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "source": self.source,
            "date": self.date,
            "venue": self.venue,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "pubmed_id": self.pubmed_id,
            "semantic_scholar_id": self.semantic_scholar_id,
            "openalex_id": self.openalex_id,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "code_url": self.code_url,
            "citation_count": self.citation_count,
            "references": self.references,
            "fields_of_study": self.fields_of_study,
            "publication_type": self.publication_type,
            "fetched_timestamp": self.fetched_timestamp,
            "source_links": self.source_links,
            "topic_tags": self.topic_tags,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "priority": self.priority,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paper":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RunStats:
    raw_candidates: int = 0
    deduplicated_candidates: int = 0
    filtered_candidates: int = 0
    llm_reranked_candidates: int = 0
    sources_checked: list[str] = field(default_factory=list)
    query_groups: list[str] = field(default_factory=list)
    lookback_days: int = 0
    near_misses: list[Paper] = field(default_factory=list)


def normalize_title(title: str) -> str:
    keep = []
    for ch in title.lower():
        keep.append(ch if ch.isalnum() else " ")
    return " ".join("".join(keep).split())
