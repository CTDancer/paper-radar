import tempfile
import unittest
from pathlib import Path

from paper_radar.models import Paper, RunStats
from paper_radar.pipeline.report import write_daily_report


class ReportTests(unittest.TestCase):
    def test_report_generation_creates_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Paper(
                title="Discrete Flow Matching for Molecules",
                authors=["A. Researcher"],
                source="arxiv",
                date="2026-06-11",
                url="https://arxiv.org/abs/0000.00000",
                topic_tags=["discrete_generative_modeling"],
                priority="Must Read",
            )
            paper.summary = {
                "Motivation and problem": "The paper targets molecular generation with discrete flow matching.",
                "Methods": "It frames generation as learning a discrete transport process.",
                "Experiments": "The test fixture does not model experiments.",
                "Innovation": "The novelty is the discrete flow-matching setup.",
                "Potential weaknesses": "The fixture does not include limitations.",
                "Insights": "The setup is relevant to molecular generation and discrete flows.",
            }
            stats = RunStats(raw_candidates=1, deduplicated_candidates=1, filtered_candidates=1)
            path = write_daily_report([paper], stats, "2026-06-12", Path(tmp), top_k=10)
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("# Daily Paper Radar", text)
            self.assertIn("## Top 1 Papers", text)
            self.assertIn("Discrete Flow Matching", text)


if __name__ == "__main__":
    unittest.main()
