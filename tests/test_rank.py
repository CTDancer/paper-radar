import unittest

from paper_radar.config import load_config
from paper_radar.models import Paper
from paper_radar.pipeline.rank import score_paper


class RankTests(unittest.TestCase):
    def setUp(self):
        self.topics = load_config("topics.yaml")
        self.ranking = load_config("ranking.yaml")

    def test_relevant_paper_scores_higher(self):
        relevant = Paper(
            title="Discrete Flow Matching for Synthesizable Molecular Design",
            abstract="We propose a novel discrete flow matching objective for reaction-based molecular generation and optimization.",
            date="2026-06-11",
            source="arxiv",
        )
        weak = Paper(
            title="A Clinical Case Study",
            abstract="This article reports a narrow clinical observation.",
            date="2026-06-11",
            source="pubmed",
        )
        self.assertGreater(score_paper(relevant, self.topics, self.ranking), score_paper(weak, self.topics, self.ranking))

    def test_penalizes_weak_dna_rna_unless_transferable(self):
        weak = Paper(
            title="RNA Editing Catalog",
            abstract="A dataset of RNA editing observations and clinical annotations.",
            date="2026-06-11",
            source="pubmed",
        )
        transferable = Paper(
            title="RNA Sequence Design with Diffusion Optimization",
            abstract="A transferable diffusion and optimization method for sequence design.",
            date="2026-06-11",
            source="arxiv",
        )
        self.assertGreater(
            score_paper(transferable, self.topics, self.ranking),
            score_paper(weak, self.topics, self.ranking),
        )


if __name__ == "__main__":
    unittest.main()
