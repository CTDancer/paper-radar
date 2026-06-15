from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paper_radar.config import REPO_ROOT, load_all_configs
from paper_radar.models import Paper, RunStats
from paper_radar.pipeline.deduplicate import deduplicate_papers
from paper_radar.pipeline.fetch import enrich_all, fetch_all, query_group_names
from paper_radar.pipeline.filter import select_candidates
from paper_radar.pipeline.rank import candidate_concerns, candidate_reason, rank_papers
from paper_radar.pipeline.storage import save_papers
from paper_radar.utils.dates import today_iso


def run_daily_candidates(
    lookback_days: int = 3,
    top_k: int = 30,
    report_date: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[Path, Path]:
    report_date = report_date or today_iso()
    configs = load_all_configs(repo_root / "config")
    raw, checked = fetch_all(configs["sources"], lookback_days)
    require_raw_candidates(raw, checked)
    deduped = deduplicate_papers(raw)
    deduped, enrichment_checked = enrich_all(deduped, configs["sources"])
    selected, eligible = select_candidates(
        deduped,
        configs["topics"],
        configs["ranking"],
        top_k=top_k,
        seen={},
        report_date=report_date,
    )
    ranked = rank_papers(selected, configs["topics"], configs["ranking"])
    stats = RunStats(
        raw_candidates=len(raw),
        deduplicated_candidates=len(deduped),
        filtered_candidates=len(eligible),
        llm_reranked_candidates=0,
        sources_checked=checked + enrichment_checked,
        query_groups=query_group_names(configs["sources"]),
        lookback_days=lookback_days,
        near_misses=eligible[top_k : top_k + 5],
    )
    json_path = write_candidate_json(ranked, stats, report_date, repo_root)
    md_path = write_candidate_markdown(ranked, stats, report_date, repo_root)
    save_papers(repo_root / "data" / "paper_radar.sqlite", ranked, report_date=None)
    return json_path, md_path


def require_raw_candidates(raw: list[Paper], checked: list[str]) -> None:
    if raw or not checked:
        return
    sources = ", ".join(checked)
    raise RuntimeError(
        "No raw candidates were fetched from any primary source. "
        f"Checked sources: {sources}. "
        "This is usually a network, DNS, rate-limit, or source-availability problem; "
        "rerun candidate generation from an environment with external network access."
    )


def candidate_payload(paper: Paper, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "title": paper.title,
        "authors": paper.authors,
        "date": paper.date,
        "source": paper.source,
        "link": paper.url or paper.pdf_url,
        "pdf_url": paper.pdf_url,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "pubmed_id": paper.pubmed_id,
        "openalex_id": paper.openalex_id,
        "semantic_scholar_id": paper.semantic_scholar_id,
        "abstract": paper.abstract,
        "venue": paper.venue,
        "code_url": paper.code_url,
        "topic_tags": paper.topic_tags,
        "deterministic_score": paper.score,
        "score_breakdown": paper.score_breakdown,
        "priority": paper.priority,
        "paper_type": paper.score_breakdown.get("paper_type", "unknown"),
        "why_selected": candidate_reason(paper),
        "possible_concerns": candidate_concerns(paper),
    }


def write_candidate_json(papers: list[Paper], stats: RunStats, report_date: str, repo_root: Path) -> Path:
    out_dir = repo_root / "data" / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_date}.json"
    payload = {
        "date": report_date,
        "stats": {
            "raw_candidates": stats.raw_candidates,
            "deduplicated_candidates": stats.deduplicated_candidates,
            "filtered_candidates": stats.filtered_candidates,
            "sources_checked": stats.sources_checked,
            "query_groups": stats.query_groups,
            "lookback_days": stats.lookback_days,
        },
        "candidates": [candidate_payload(paper, idx) for idx, paper in enumerate(papers, 1)],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_candidate_markdown(papers: list[Paper], stats: RunStats, report_date: str, repo_root: Path) -> Path:
    out_dir = repo_root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_date}.candidates.md"
    lines = [
        f"# Paper Radar Candidates — {report_date}",
        "",
        "This is a candidate packet for Codex-mode report writing, not a final daily report.",
        "",
        "## Search Log",
        "",
        f"- Sources checked: {', '.join(stats.sources_checked)}",
        f"- Lookback window: {stats.lookback_days} days",
        f"- Raw candidates: {stats.raw_candidates}",
        f"- Deduplicated candidates: {stats.deduplicated_candidates}",
        f"- Candidate count: {len(papers)}",
        "",
        "## Candidates",
        "",
    ]
    for idx, paper in enumerate(papers, 1):
        payload = candidate_payload(paper, idx)
        lines.extend(
            [
                f"### {idx}. {paper.title}",
                "",
                f"**Authors:** {', '.join(paper.authors[:8]) or 'Unknown'}",
                f"**Date:** {paper.date or 'Unknown'}",
                f"**Source:** {paper.source or 'Unknown'}",
                f"**Link:** {payload['link'] or 'No link available'}",
                f"**Code:** {paper.code_url or 'Not found'}",
                f"**Tags:** {', '.join(paper.topic_tags) or 'untagged'}",
                f"**Priority hint:** {paper.priority}",
                f"**Paper type:** {payload['paper_type']}",
                f"**Score:** {paper.score}",
                f"**Why selected:** {payload['why_selected']}",
                f"**Possible concerns:** {payload['possible_concerns']}",
                "",
                f"**Abstract:** {paper.abstract or 'No abstract available.'}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
