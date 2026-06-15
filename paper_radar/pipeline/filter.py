from __future__ import annotations

from typing import Any

from paper_radar.models import Paper
from paper_radar.pipeline.rank import rank_papers, score_paper


def filter_candidates(
    papers: list[Paper],
    topics_config: dict[str, Any],
    ranking_config: dict[str, Any],
    seen: dict[str, dict[str, str]] | None = None,
    report_date: str | None = None,
) -> list[Paper]:
    """Return only strict-threshold, not-previously-shown candidates.

    Kept for tests and small pipeline calls. The daily workflow uses
    select_candidates so it can backfill to top_k when the strict pool is small.
    """
    minimum = float(ranking_config.get("minimum_filter_score", 4.0))
    filtered: list[Paper] = []
    seen = seen or {}
    for paper in papers:
        key = paper.canonical_key()
        if was_seen_on_another_day(seen, key, report_date):
            continue
        score_paper(paper, topics_config, ranking_config)
        if paper.score >= minimum:
            filtered.append(paper)
    return filtered


def select_candidates(
    papers: list[Paper],
    topics_config: dict[str, Any],
    ranking_config: dict[str, Any],
    top_k: int,
    seen: dict[str, dict[str, str]] | None = None,
    report_date: str | None = None,
) -> tuple[list[Paper], list[Paper]]:
    """Select daily papers with strict ranking plus a softer backfill tier.

    The strict tier keeps quality high. The backfill tier prevents short reports
    when source APIs are sparse, rate-limited, or when seen-paper tracking removes
    many otherwise reasonable candidates.
    """
    minimum = float(ranking_config.get("minimum_filter_score", 4.0))
    backfill_minimum = float(
        ranking_config.get("backfill_minimum_score", max(0.0, minimum - 3.0))
    )
    allow_seen_backfill = bool(ranking_config.get("allow_seen_backfill", True))
    seen = seen or {}

    fresh_or_same_day: list[Paper] = []
    previously_seen: list[Paper] = []
    for paper in papers:
        score_paper(paper, topics_config, ranking_config)
        if was_seen_on_another_day(seen, paper.canonical_key(), report_date):
            previously_seen.append(paper)
        else:
            fresh_or_same_day.append(paper)

    strict = rank_papers(
        [paper for paper in fresh_or_same_day if paper.score >= minimum],
        topics_config,
        ranking_config,
    )
    backfill = rank_papers(
        [
            paper
            for paper in fresh_or_same_day
            if backfill_minimum <= paper.score < minimum
        ],
        topics_config,
        ranking_config,
    )
    seen_backfill = (
        rank_papers(
            [paper for paper in previously_seen if paper.score >= backfill_minimum],
            topics_config,
            ranking_config,
        )
        if allow_seen_backfill
        else []
    )

    final_backfill = rank_papers(
        [
            paper
            for paper in [*fresh_or_same_day, *previously_seen]
            if paper.score < backfill_minimum
        ],
        topics_config,
        ranking_config,
    )

    candidate_order = [*strict, *backfill, *seen_backfill, *final_backfill]
    selected = take_unique(candidate_order, top_k)
    eligible = take_unique(candidate_order, len(papers))
    return selected, eligible


def was_seen_on_another_day(
    seen: dict[str, dict[str, str]], key: str, report_date: str | None
) -> bool:
    return key in seen and seen[key].get("last_shown") != report_date


def take_unique(papers: list[Paper], limit: int) -> list[Paper]:
    selected: list[Paper] = []
    keys: set[str] = set()
    for paper in papers:
        key = paper.canonical_key()
        if key in keys:
            continue
        selected.append(paper)
        keys.add(key)
        if len(selected) >= limit:
            break
    return selected
