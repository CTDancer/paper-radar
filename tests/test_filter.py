import unittest

from paper_radar.config import load_config
from paper_radar.models import Paper
from paper_radar.pipeline.filter import select_candidates


class SelectCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.topics = load_config("topics.yaml")
        self.ranking = load_config("ranking.yaml")

    def test_backfills_to_top_k_with_plausible_candidates(self):
        papers = [
            Paper(
                title=f"Diffusion model candidate {idx}",
                abstract="A generative model paper with diffusion sampling for useful transferable modeling.",
                date="2026-06-11",
                source="arxiv",
            )
            for idx in range(12)
        ]
        selected, eligible = select_candidates(
            papers,
            self.topics,
            self.ranking,
            top_k=10,
            seen={},
            report_date="2026-06-12",
        )
        self.assertEqual(len(selected), 10)
        self.assertGreaterEqual(len(eligible), 10)


    def test_force_fills_from_best_remaining_candidates(self):
        papers = [
            Paper(
                title=f"Mostly unrelated candidate {idx}",
                abstract="A broad machine learning article with limited direct overlap.",
                date="2026-06-11",
                source="arxiv",
            )
            for idx in range(11)
        ]
        selected, eligible = select_candidates(
            papers,
            self.topics,
            self.ranking,
            top_k=10,
            seen={},
            report_date="2026-06-12",
        )
        self.assertEqual(len(selected), 10)
        self.assertGreaterEqual(len(eligible), 10)


if __name__ == "__main__":
    unittest.main()
