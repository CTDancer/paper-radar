from __future__ import annotations

from pathlib import Path
from typing import Any

from paper_radar.config import REPO_ROOT, load_all_configs, reports_dir
from paper_radar.models import RunStats
from paper_radar.pipeline.deduplicate import deduplicate_papers
from paper_radar.pipeline.fetch import enrich_all, fetch_all, query_group_names
from paper_radar.pipeline.filter import select_candidates
from paper_radar.pipeline.rank import rank_papers
from paper_radar.pipeline.report import write_daily_report
from paper_radar.pipeline.storage import load_seen, save_papers, update_seen
from paper_radar.pipeline.summarize import summarize_papers
from paper_radar.pipeline.validate import validate_final_report, validate_selected_papers
from paper_radar.utils.dates import today_iso


def run_daily(
    lookback_days: int = 3,
    top_k: int = 10,
    report_date: str | None = None,
    repo_root: Path = REPO_ROOT,
    use_llm: bool = True,
) -> Path:
    report_date = report_date or today_iso()
    configs = load_all_configs(repo_root / "config")
    raw, checked = fetch_all(configs["sources"], lookback_days)
    deduped = deduplicate_papers(raw)
    deduped, enrichment_checked = enrich_all(deduped, configs["sources"])
    seen = load_seen(repo_root / "data" / "seen_papers.json")
    selected_pool, eligible = select_candidates(
        deduped,
        configs["topics"],
        configs["ranking"],
        top_k=top_k,
        seen=seen,
        report_date=report_date,
    )
    pool_size = int(configs["ranking"].get("stage_1_pool_size", 50))
    rerank_pool = eligible[:pool_size]
    selected = summarize_papers(selected_pool[:top_k], use_llm=use_llm, require_llm=True)
    selected_keys = {paper.canonical_key() for paper in selected}
    near_misses = [
        paper for paper in rerank_pool if paper.canonical_key() not in selected_keys
    ][:5]

    stats = RunStats(
        raw_candidates=len(raw),
        deduplicated_candidates=len(deduped),
        filtered_candidates=len(eligible),
        llm_reranked_candidates=0,
        sources_checked=checked + enrichment_checked,
        query_groups=query_group_names(configs["sources"]),
        lookback_days=lookback_days,
        near_misses=near_misses,
    )
    selected_validation = validate_selected_papers(selected)
    if not selected_validation.ok:
        raise RuntimeError("Selected papers failed quality validation: " + "; ".join(selected_validation.errors))
    report_path = write_daily_report(selected, stats, report_date, reports_dir(repo_root), top_k=top_k)
    report_validation = validate_final_report(report_path.read_text(encoding="utf-8"), candidates_available=len(eligible))
    if not report_validation.ok:
        raise RuntimeError("Final report failed quality validation: " + "; ".join(report_validation.errors))
    save_papers(repo_root / "data" / "paper_radar.sqlite", eligible, report_date=None)
    save_papers(repo_root / "data" / "paper_radar.sqlite", selected, report_date=report_date)
    update_seen(repo_root / "data" / "seen_papers.json", selected, report_date)
    return report_path


def run_fetch_only(lookback_days: int = 3, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    configs = load_all_configs(repo_root / "config")
    raw, checked = fetch_all(configs["sources"], lookback_days)
    deduped = deduplicate_papers(raw)
    deduped, enrichment_checked = enrich_all(deduped, configs["sources"])
    save_papers(repo_root / "data" / "paper_radar.sqlite", deduped)
    return {"raw": len(raw), "deduplicated": len(deduped), "sources": checked + enrichment_checked}
