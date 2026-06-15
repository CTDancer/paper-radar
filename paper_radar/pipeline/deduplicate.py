from __future__ import annotations

from paper_radar.models import Paper
from paper_radar.utils.text import fuzzy_ratio


def deduplicate_papers(papers: list[Paper], fuzzy_threshold: float = 0.92) -> list[Paper]:
    merged: list[Paper] = []
    id_index: dict[str, Paper] = {}

    for paper in papers:
        match = None
        for key in paper.identifier_keys():
            if key in id_index:
                match = id_index[key]
                break
        if match is None:
            for existing in merged:
                if fuzzy_ratio(paper.normalized_title(), existing.normalized_title()) >= fuzzy_threshold:
                    match = existing
                    break
        if match is None:
            merged.append(paper)
            for key in paper.identifier_keys():
                id_index[key] = paper
        else:
            match.merge(paper)
            for key in match.identifier_keys():
                id_index[key] = match
    return merged
