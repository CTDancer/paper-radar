from __future__ import annotations

from paper_radar.models import Paper


def summary_prompt(paper: Paper) -> str:
    return f"""Summarize this paper conservatively for a PhD student interested in generative modeling, optimization, and AI drug discovery. In the `Insights` section, focus on method, theory, design patterns, or field-level lessons; do not force a connection to a specific personal project.

Use exactly these section labels:
Motivation and problem
Methods
Experiments
Innovation
Potential weaknesses
Insights

Do not invent code links, experimental claims, limitations, or formulas not supported by the abstract. If something is unclear, say it is unclear from the abstract.

Title: {paper.title}
Authors: {', '.join(paper.authors)}
Date: {paper.date}
Source: {paper.source}
Venue: {paper.venue}
Abstract: {paper.abstract}
Topic tags: {', '.join(paper.topic_tags)}
"""
