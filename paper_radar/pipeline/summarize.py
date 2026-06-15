from __future__ import annotations

from paper_radar.llm.client import LLMClient
from paper_radar.llm.prompts import summary_prompt
from paper_radar.models import Paper

SECTION_KEYS = [
    "Motivation and problem",
    "Methods",
    "Experiments",
    "Innovation",
    "Potential weaknesses",
    "Insights",
]


def summarize_papers(papers: list[Paper], use_llm: bool = True, require_llm: bool = False) -> list[Paper]:
    client = LLMClient()
    if require_llm and (not use_llm or not client.available):
        raise RuntimeError("API final-report mode requires OPENAI_API_KEY. Use daily-candidates for Codex mode.")
    for paper in papers:
        llm_text = client.complete(summary_prompt(paper)) if use_llm and client.available else ""
        if require_llm and not llm_text:
            raise RuntimeError(f"LLM summary failed for paper: {paper.title}")
        paper.summary = parse_llm_summary(llm_text) if llm_text else fallback_summary(paper)
    return papers


def parse_llm_summary(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.strip("*: ")
        if normalized in SECTION_KEYS:
            current = normalized
            parsed[current] = ""
        elif current:
            parsed[current] = f"{parsed[current]} {line}".strip()
    for key in SECTION_KEYS:
        parsed.setdefault(key, "Unclear from the available abstract and metadata.")
    return parsed


def fallback_summary(paper: Paper) -> dict[str, str]:
    abstract = paper.abstract or "No abstract was available from the source metadata."
    tags = ", ".join(paper.topic_tags[:4]) or "the configured research interests"
    return {
        "Motivation and problem": (
            f"This paper appears relevant to {tags}. Based on the available metadata, the problem setting is: {abstract[:450]}"
        ),
        "Methods": (
            "The degraded-mode candidate note cannot explain the full method. Codex-mode final reports must replace this with a clear whole-paper methods explanation."
        ),
        "Experiments": (
            "Experimental details are unclear from the available metadata unless they are explicitly described in the abstract."
        ),
        "Innovation": (
            "The apparent innovation should be verified from the paper text; from the abstract, the novelty signal is captured by the ranking terms and topic matches."
        ),
        "Potential weaknesses": (
            "Limitations are unclear from the abstract alone. Treat this summary as a reading triage note, not a substitute for reading the paper."
        ),
        "Insights": (
            f"The useful insight should come from the paper's method, theory, design pattern, or empirical lesson, not merely from matching topic tags."
        ),
    }
