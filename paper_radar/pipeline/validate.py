from __future__ import annotations

import re
from dataclasses import dataclass, field

from paper_radar.models import Paper


BANNED_FINAL_REPORT_PHRASES = [
    "This paper appears relevant to",
    "The current degraded-mode summarizer",
    "Based on the available metadata",
    "The apparent innovation should be verified",
    "Experimental details are unclear unless",
    "Check whether its formulation transfers",
    "Limitations are unclear from the abstract alone",
    "Unclear from available metadata",
]


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_final_report(text: str, candidates_available: int | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for phrase in BANNED_FINAL_REPORT_PHRASES:
        if phrase.lower() in text.lower():
            errors.append(f"Final report contains banned fallback phrase: {phrase}")

    generic_unclear = len(re.findall(r"unclear from (?:the )?(?:available )?(?:metadata|abstract)", text, flags=re.I))
    if generic_unclear > 2:
        errors.append("More than two generic unclear-from-metadata statements appear in the report.")

    headings = re.findall(r"^### \d+\.", text, flags=re.M)
    if candidates_available is not None and candidates_available >= 10 and len(headings) < 10:
        errors.append("Report has fewer than 10 papers even though at least 10 candidates were available.")

    sections = re.findall(r"\*\*(Motivation and problem|Methods|Experiments|Innovation|Potential weaknesses|Insights)\.\*\*\s*(.+)", text)
    seen_sections: dict[str, int] = {}
    for _, body in sections:
        normalized = re.sub(r"\W+", " ", body.lower()).strip()
        if len(normalized) > 80:
            seen_sections[normalized] = seen_sections.get(normalized, 0) + 1
    if any(count > 1 for count in seen_sections.values()):
        errors.append("At least one long summary section is repeated across multiple papers.")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def validate_selected_papers(papers: list[Paper]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if papers:
        first_type = papers[0].score_breakdown.get("paper_type")
        if first_type == "routine_application":
            errors.append("#1 paper is a routine application without clear method novelty.")
    for paper in papers:
        if paper.priority == "Must Read":
            novelty = float(paper.score_breakdown.get("novelty", 0.0))
            paper_type = paper.score_breakdown.get("paper_type")
            if novelty < 1.0 and paper_type not in {"method", "benchmark_dataset", "transferable_method"}:
                errors.append(f"Must Read paper lacks novelty evidence: {paper.title}")
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
