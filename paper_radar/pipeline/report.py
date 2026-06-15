from __future__ import annotations

from pathlib import Path

from paper_radar.models import Paper, RunStats


def write_daily_report(
    papers: list[Paper],
    stats: RunStats,
    report_date: str,
    reports_dir: Path,
    top_k: int = 10,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{report_date}.md"
    selected = papers[:top_k]
    lines = render_daily_report(selected, stats, report_date, top_k)
    path.write_text(lines, encoding="utf-8")
    return path


def render_daily_report(papers: list[Paper], stats: RunStats, report_date: str, top_k: int = 10) -> str:
    themes = main_themes(papers)
    most_important = papers[0].title.rstrip(".") if papers else "No sufficiently relevant paper was found"
    if len(papers) < top_k:
        shortage = (
            f" Fewer than {top_k} papers are included because only {len(papers)} candidates passed the configured relevance filter."
        )
    else:
        shortage = ""

    lines: list[str] = [
        f"# Daily Paper Radar — {report_date}",
        "",
        "## Overview",
        "",
        (
            f"Today I found {stats.raw_candidates} raw candidates from {', '.join(stats.sources_checked) or 'no sources'}. "
            f"After deduplication and filtering, {stats.filtered_candidates} candidates remained.{shortage}"
        ),
        "",
        f"The top papers mainly focus on {themes or 'no dominant configured theme'}.",
        "",
        f"The most important paper today is **{most_important}**.",
        "",
        f"A surprising trend or idea: {surprising_trend(papers)}",
        "",
        f"## Top {min(top_k, len(papers))} Papers",
        "",
    ]
    for idx, paper in enumerate(papers, 1):
        lines.extend(render_paper(idx, paper))
    lines.extend(render_near_misses(stats.near_misses))
    lines.extend(
        [
            "## Search Log",
            "",
            f"- Sources checked: {', '.join(stats.sources_checked)}",
            f"- Query groups used: {', '.join(stats.query_groups)}",
            f"- Lookback window: {stats.lookback_days} days",
            f"- Raw candidates: {stats.raw_candidates}",
            f"- Deduplicated candidates: {stats.deduplicated_candidates}",
            f"- Filtered candidates: {stats.filtered_candidates}",
            f"- LLM-reranked candidates: {stats.llm_reranked_candidates}",
            "",
        ]
    )
    return "\n".join(lines)


def render_paper(rank: int, paper: Paper) -> list[str]:
    summary = paper.summary or {}
    authors = ", ".join(paper.authors[:8]) + (" et al." if len(paper.authors) > 8 else "")
    code = paper.code_url or "Not found in metadata"
    tags = ", ".join(paper.topic_tags) or "untagged"
    link = paper.url or paper.pdf_url or "No link available"
    return [
        f"### {rank}. {paper.title}",
        "",
        f"**Authors:** {authors or 'Unknown'}",
        f"**Date:** {paper.date or 'Unknown'}",
        f"**Source:** {paper.source or 'Unknown'}",
        f"**Link:** {link}",
        f"**Code:** {code}",
        f"**Tags:** {tags}",
        f"**Priority:** {paper.priority}",
        "",
        f"**Motivation and problem.** {summary.get('Motivation and problem', 'Unclear from available metadata.')}",
        "",
        f"**Methods.** {summary.get('Methods', 'Unclear from available metadata.')}",
        "",
        f"**Experiments.** {summary.get('Experiments', 'Unclear from available metadata.')}",
        "",
        f"**Innovation.** {summary.get('Innovation', 'Unclear from available metadata.')}",
        "",
        f"**Potential weaknesses.** {summary.get('Potential weaknesses', 'Unclear from available metadata.')}",
        "",
        f"**Insights.** {summary.get('Insights', 'Unclear from available metadata.')}",
        "",
    ]


def render_near_misses(near_misses: list[Paper]) -> list[str]:
    lines = ["## Near Misses", ""]
    if not near_misses:
        lines.extend(["No near misses were recorded.", ""])
        return lines
    for paper in near_misses[:5]:
        reason = "close relevance score but below the final top-paper cutoff"
        lines.append(f"- **{paper.title}** — {reason}.")
    lines.append("")
    return lines


def main_themes(papers: list[Paper]) -> str:
    counts: dict[str, int] = {}
    for paper in papers:
        for tag in paper.topic_tags:
            counts[tag] = counts.get(tag, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    return ", ".join(tag for tag, _ in ordered)


def surprising_trend(papers: list[Paper]) -> str:
    if not papers:
        return "none, because no papers passed the filter"
    tags = {tag for paper in papers for tag in paper.topic_tags}
    if "molecular_glue_and_tpd" in tags:
        return "targeted protein degradation or molecular glue work showed up alongside generative and optimization methods"
    if "enamine_real_and_reaction_based_design" in tags:
        return "reaction-aware and make-on-demand molecular design appeared in the candidate pool"
    if "discrete_generative_modeling" in tags:
        return "discrete generative modeling continues to connect naturally with optimization-style search"
    return "the selected papers mostly reinforce the configured core themes rather than a single unusual trend"
