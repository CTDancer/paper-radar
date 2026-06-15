from __future__ import annotations

import logging
from typing import Any

from paper_radar.models import Paper
from paper_radar.sources import (
    ArxivFetcher,
    BioRxivFetcher,
    ChemRxivFetcher,
    CrossrefFetcher,
    DBLPEnricher,
    EuropePMCFetcher,
    OpenAlexFetcher,
    OpenReviewFetcher,
    PapersWithCodeEnricher,
    PubMedFetcher,
    SemanticScholarFetcher,
    UnpaywallEnricher,
)

LOGGER = logging.getLogger(__name__)

FETCHERS = {
    "arxiv": ArxivFetcher,
    "openalex": OpenAlexFetcher,
    "semantic_scholar": SemanticScholarFetcher,
    "pubmed": PubMedFetcher,
    "europe_pmc": EuropePMCFetcher,
    "openreview": OpenReviewFetcher,
    "biorxiv": BioRxivFetcher,
    "chemrxiv": ChemRxivFetcher,
    "crossref": CrossrefFetcher,
}

ENRICHERS = {
    "unpaywall": UnpaywallEnricher,
    "papers_with_code": PapersWithCodeEnricher,
    "dblp": DBLPEnricher,
}


def fetch_all(sources_config: dict[str, Any], lookback_days: int) -> tuple[list[Paper], list[str]]:
    max_results = int(sources_config.get("max_results_per_source", 80))
    timeout = int(sources_config.get("request_timeout_seconds", 30))
    max_failures = int(sources_config.get("max_failures_per_source", 3))
    papers: list[Paper] = []
    checked: list[str] = []
    for source_name, source_settings in sources_config.get("sources", {}).items():
        if not source_settings.get("enabled", True) or source_settings.get("mode") == "enrichment":
            continue
        fetcher_cls = FETCHERS.get(source_name)
        if fetcher_cls is None:
            LOGGER.info("Source %s is configured but no fetcher is implemented; skipping", source_name)
            continue
        checked.append(source_name)
        fetcher = fetcher_cls(
            timeout=timeout,
            max_results=int(source_settings.get("max_results", max_results)),
            max_failures=int(source_settings.get("max_failures", max_failures)),
            settings=source_settings,
        )
        source_queries = queries_for_source(sources_config, source_settings)
        try:
            source_papers = fetcher.fetch(source_queries, lookback_days)
            log_source_result(source_name, source_papers, fetcher.request_errors, fetcher.error_summary())
            papers.extend(source_papers)
        except Exception as exc:
            LOGGER.info("%s fetched 0 candidates (source failed: %s)", source_name, exc)
            LOGGER.debug("%s fetch traceback", source_name, exc_info=True)
    return papers, checked


def enrich_all(papers: list[Paper], sources_config: dict[str, Any]) -> tuple[list[Paper], list[str]]:
    timeout = int(sources_config.get("request_timeout_seconds", 30))
    max_failures = int(sources_config.get("max_failures_per_source", 3))
    checked: list[str] = []
    for source_name, source_settings in sources_config.get("sources", {}).items():
        if not source_settings.get("enabled", True) or source_settings.get("mode") != "enrichment":
            continue
        enricher_cls = ENRICHERS.get(source_name)
        if enricher_cls is None:
            LOGGER.info("Enrichment source %s is configured but no enricher is implemented; skipping", source_name)
            continue
        checked.append(source_name)
        enricher = enricher_cls(
            timeout=timeout,
            max_results=int(source_settings.get("max_results", len(papers))),
            max_failures=int(source_settings.get("max_failures", max_failures)),
            settings=source_settings,
        )
        try:
            papers = enricher.enrich(papers)
            issue_summary = enricher.error_summary()
            if issue_summary:
                LOGGER.info("%s enrichment completed (%s)", source_name, issue_summary)
            else:
                LOGGER.info("%s enrichment completed", source_name)
        except Exception as exc:
            LOGGER.info("%s enrichment skipped (source failed: %s)", source_name, exc)
            LOGGER.debug("%s enrichment traceback", source_name, exc_info=True)
    return papers, checked


def queries_for_source(sources_config: dict[str, Any], source_settings: dict[str, Any]) -> list[str]:
    groups = sources_config.get("query_groups", [])
    if isinstance(groups, list):
        return groups
    selected = source_settings.get("query_groups") or list(groups.keys())
    queries: list[str] = []
    for name in selected:
        values = groups.get(name, [])
        if isinstance(values, str):
            queries.append(values)
        else:
            queries.extend(values)
    return [query for query in queries if query]


def query_group_names(sources_config: dict[str, Any]) -> list[str]:
    groups = sources_config.get("query_groups", [])
    if isinstance(groups, dict):
        return list(groups.keys())
    if isinstance(groups, list):
        return groups
    return []


def log_source_result(source_name: str, source_papers: list[Paper], errors: list[str], issue_summary: str) -> None:
    if issue_summary and source_papers:
        LOGGER.info(
            "%s fetched %d candidates (%d request issue(s): %s)",
            source_name,
            len(source_papers),
            len(errors),
            issue_summary,
        )
    elif issue_summary:
        LOGGER.info(
            "%s fetched 0 candidates (source unavailable or rate-limited: %s)",
            source_name,
            issue_summary,
        )
    else:
        LOGGER.info("%s fetched %d candidates", source_name, len(source_papers))
