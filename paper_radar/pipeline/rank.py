from __future__ import annotations

import re
from typing import Any

from paper_radar.models import Paper
from paper_radar.utils.dates import recency_score
from paper_radar.utils.text import citation_signal, contains_any, count_term_hits


NOVELTY_TERMS = [
    "new",
    "novel",
    "introduce",
    "propose",
    "framework",
    "benchmark",
    "dataset",
    "objective",
    "algorithm",
    "formulation",
    "theory",
    "sampler",
    "training objective",
]
METHOD_TERMS = [
    "method",
    "algorithm",
    "objective",
    "training",
    "sampler",
    "inference",
    "optimization",
    "flow matching",
    "diffusion",
    "gflownet",
]
REVIEW_TERMS = ["survey", "review", "perspective", "tutorial", "primer", "dissertation", "thesis", "editorial"]
ROUTINE_APPLICATION_TERMS = [
    "molecular docking",
    "molecular dynamics",
    "admet",
    "qsar",
    "virtual screening",
    "network pharmacology",
    "pharmacokinetic",
    "pharmacokinetics",
    "in silico",
]
METHOD_NOVELTY_TERMS = [
    "we propose",
    "we introduce",
    "we present",
    "novel method",
    "new method",
    "new algorithm",
    "new objective",
    "training objective",
    "benchmark",
    "dataset",
    "theoretical",
]
DRUG_TERMS = ["drug", "molecule", "ligand", "protein", "docking", "binding", "protac", "molecular glue"]
GEN_TERMS = ["generative", "diffusion", "flow matching", "gflownet", "autoregressive", "sampler"]
OPT_TERMS = ["optimization", "bayesian optimization", "pareto", "search", "reinforcement learning", "evolutionary"]
PROJECT_TERMS = ["molecular glue", "protac", "enamine real", "reaction-based", "gflownet", "discrete flow"]
APPLIED_DISTRACTOR_TERMS = [
    "wildfire",
    "gravitational wave",
    "radio telescope",
    "human reconstruction",
    "dexterous manipulation",
]


def rank_papers(
    papers: list[Paper],
    topics_config: dict[str, Any],
    ranking_config: dict[str, Any],
) -> list[Paper]:
    for paper in papers:
        score_paper(paper, topics_config, ranking_config)
    return sorted(papers, key=lambda p: p.score, reverse=True)


def score_paper(paper: Paper, topics_config: dict[str, Any], ranking_config: dict[str, Any]) -> float:
    weights = ranking_config.get("weights", {})
    penalties = ranking_config.get("penalties", {})
    text = f"{paper.title} {paper.abstract} {' '.join(paper.fields_of_study)}".lower()
    title_text = f"{paper.title} {paper.publication_type}".lower()

    topic_score, tags = topic_match_score(text, topics_config)
    paper.topic_tags = tags
    paper_type = classify_paper(paper)
    breakdown: dict[str, float] = {"paper_type": paper_type}

    direct = min(6.0, topic_score)
    novelty_raw = novelty_signal(text)
    method_raw = methodological_signal(text)
    transferable_raw = transferable_insight_signal(text, topics_config, paper_type)
    drug = 1.0 if contains_any(text, DRUG_TERMS) else 0.0
    gen = 1.0 if contains_any(text, GEN_TERMS) else 0.0
    opt = 1.0 if contains_any(text, OPT_TERMS) else 0.0
    project = 1.0 if contains_any(text, PROJECT_TERMS) else 0.0
    credibility = source_credibility(paper.source)
    code = 1.0 if paper.code_url else 0.0
    recency = recency_score(paper.date)
    citations = citation_signal(paper.citation_count)

    breakdown["direct_relevance"] = direct * weights.get("direct_relevance", 1.0)
    breakdown["novelty"] = novelty_raw * weights.get("novelty", 1.0)
    breakdown["methodological_insight"] = method_raw * weights.get("methodological_insight", 1.0)
    breakdown["transferable_insight"] = transferable_raw * weights.get("transferable_insight", 1.0)
    breakdown["drug_discovery_relevance"] = drug * weights.get("drug_discovery_relevance", 1.0)
    breakdown["generative_modeling_relevance"] = gen * weights.get("generative_modeling_relevance", 1.0)
    breakdown["optimization_relevance"] = opt * weights.get("optimization_relevance", 1.0)
    breakdown["current_project_relevance"] = project * weights.get("current_project_relevance", 1.0)
    breakdown["source_credibility"] = credibility * weights.get("source_credibility", 1.0)
    breakdown["code_availability"] = code * weights.get("code_availability", 1.0)
    breakdown["recency"] = recency * weights.get("recency", 1.0)
    breakdown["citation_signal"] = citations * weights.get("citation_signal", 1.0)

    penalty = 0.0
    if contains_any(title_text, REVIEW_TERMS):
        penalty += penalties.get("review_paper", 0.0)
    if direct < 1.5:
        penalty += penalties.get("weak_relevance", 0.0)
    low_priority = topics_config.get("low_priority_terms", [])
    transfer_terms = topics_config.get("transfer_terms", [])
    if contains_any(text, low_priority) and not contains_any(text, transfer_terms):
        penalty += penalties.get("dna_rna_unless_transferable", 0.0)
    if paper_type == "routine_application":
        penalty += penalties.get("routine_application", 7.0)
    if not paper.abstract or len(paper.abstract) < 250:
        penalty += penalties.get("missing_or_vague_abstract", 2.0)
    if contains_any(text, APPLIED_DISTRACTOR_TERMS) and not (drug or opt or project):
        penalty += 3.0
    breakdown["penalties"] = -penalty

    paper.score_breakdown = breakdown
    paper.score = round(sum(v for v in breakdown.values() if isinstance(v, (int, float))), 3)
    paper.priority = priority_from_evidence(paper.score, paper_type, novelty_raw, method_raw, project, gen, opt)
    return paper.score


def novelty_signal(text: str) -> float:
    return min(3.0, count_term_hits(text, NOVELTY_TERMS) * 0.3 + count_term_hits(text, METHOD_NOVELTY_TERMS) * 0.7)


def methodological_signal(text: str) -> float:
    return min(3.0, count_term_hits(text, METHOD_TERMS) * 0.32)


def transferable_insight_signal(text: str, topics_config: dict[str, Any], paper_type: str) -> float:
    if paper_type in {"review", "routine_application", "weak_match"}:
        return 0.0
    transfer_hits = count_term_hits(text, topics_config.get("transfer_terms", []))
    method_hits = count_term_hits(text, METHOD_TERMS + METHOD_NOVELTY_TERMS)
    return min(3.0, transfer_hits * 0.25 + method_hits * 0.18)


def classify_paper(paper: Paper) -> str:
    text = f"{paper.title} {paper.abstract} {paper.publication_type}".lower()
    if contains_any(text, REVIEW_TERMS):
        return "review"
    methodish = contains_any(text, METHOD_NOVELTY_TERMS) or contains_any(text, METHOD_TERMS)
    routine = contains_any(text, ROUTINE_APPLICATION_TERMS)
    if routine and not contains_any(text, METHOD_NOVELTY_TERMS):
        return "routine_application"
    if contains_any(text, ["benchmark", "dataset"]):
        return "benchmark_dataset"
    if methodish:
        return "method"
    if contains_any(text, DRUG_TERMS):
        return "application"
    if contains_any(text, GEN_TERMS + OPT_TERMS):
        return "transferable_method"
    return "weak_match"


def candidate_reason(paper: Paper) -> str:
    paper_type = str(paper.score_breakdown.get("paper_type", classify_paper(paper)))
    tags = ", ".join(paper.topic_tags[:4]) or "configured topics"
    if paper_type == "method":
        return f"Selected because it looks like a method paper connected to {tags}."
    if paper_type == "benchmark_dataset":
        return f"Selected because it may introduce a benchmark or dataset relevant to {tags}."
    if paper_type == "routine_application":
        return f"Selected only as a lower-priority candidate: it matches {tags}, but appears application-driven."
    if paper_type == "transferable_method":
        return f"Selected because it may contain a transferable modeling or optimization idea related to {tags}."
    return f"Selected as a possible match to {tags}, but Codex should verify novelty before final inclusion."


def candidate_concerns(paper: Paper) -> str:
    concerns: list[str] = []
    paper_type = str(paper.score_breakdown.get("paper_type", classify_paper(paper)))
    if paper_type == "routine_application":
        concerns.append("appears to use standard docking/MD/ADMET/QSAR or virtual-screening tools")
    if paper_type in {"review", "weak_match"}:
        concerns.append(f"classified as {paper_type}")
    if not paper.abstract or len(paper.abstract) < 250:
        concerns.append("abstract is missing or too short to judge novelty well")
    if paper.priority == "Must Read" and paper.score_breakdown.get("novelty", 0) < 1.0:
        concerns.append("high priority may not be justified by novelty evidence")
    return "; ".join(concerns) if concerns else "No obvious concern from metadata; still verify from the abstract."


def topic_match_score(text: str, topics_config: dict[str, Any]) -> tuple[float, list[str]]:
    total = 0.0
    tags: list[str] = []
    for group, settings in topics_config.get("topic_groups", {}).items():
        terms = settings.get("terms", [])
        hits = count_term_hits(text, terms)
        if hits:
            tags.append(group)
            total += min(2.0, hits * 0.45) * float(settings.get("weight", 1.0))
    return total, tags


def source_credibility(source: str) -> float:
    sources = set(re.split(r"\+", source or ""))
    score = 0.0
    if "arxiv" in sources:
        score += 0.8
    if "openalex" in sources:
        score += 0.7
    if "semantic_scholar" in sources:
        score += 0.8
    if "pubmed" in sources:
        score += 1.0
    if "europe_pmc" in sources:
        score += 0.9
    if "openreview" in sources:
        score += 0.8
    if "biorxiv" in sources:
        score += 0.7
    if "chemrxiv" in sources:
        score += 0.7
    if "crossref" in sources:
        score += 0.6
    return min(1.5, score)


def priority_from_evidence(
    score: float,
    paper_type: str,
    novelty_raw: float,
    method_raw: float,
    project: float,
    gen: float,
    opt: float,
) -> str:
    methodologically_interesting = paper_type in {"method", "benchmark_dataset", "transferable_method"}
    if paper_type == "review":
        return "Skim" if score >= 10 else "Archive"
    if paper_type == "routine_application":
        return "Skim" if score >= 10 else "Archive"
    if score >= 18 and methodologically_interesting and (novelty_raw >= 1.0 or method_raw >= 1.0 or project):
        return "Must Read"
    if score >= 12 and methodologically_interesting:
        return "Strong Skim"
    if score >= 7:
        return "Skim"
    return "Archive"
