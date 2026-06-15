import tempfile
import unittest
from pathlib import Path

from paper_radar.config import load_config
from paper_radar.models import Paper, RunStats
from paper_radar.pipeline.candidates import require_raw_candidates, write_candidate_json, write_candidate_markdown
from paper_radar.pipeline.rank import classify_paper, score_paper
from paper_radar.pipeline.report import write_daily_report
from paper_radar.pipeline.summarize import fallback_summary
from paper_radar.pipeline.validate import BANNED_FINAL_REPORT_PHRASES, validate_final_report


class QualityWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.topics = load_config("topics.yaml")
        self.ranking = load_config("ranking.yaml")

    def test_routine_docking_application_is_not_must_read(self):
        paper = Paper(
            title="Pharmacokinetics, molecular docking, and molecular dynamics simulation of natural products",
            abstract="We apply ADMET, molecular docking, and molecular dynamics simulation to screen compounds against a disease target.",
            source="openalex",
            date="2026-06-11",
        )
        score_paper(paper, self.topics, self.ranking)
        self.assertEqual(classify_paper(paper), "routine_application")
        self.assertNotEqual(paper.priority, "Must Read")

    def test_method_paper_outranks_routine_application(self):
        method = Paper(
            title="Discrete Flow Matching with a New Training Objective for Molecular Design",
            abstract="We propose a new discrete flow matching training objective and sampler for synthesizable molecular generation and optimization.",
            source="arxiv",
            date="2026-06-11",
        )
        routine = Paper(
            title="Molecular docking and MD simulation for one disease target",
            abstract="We apply molecular docking, ADMET, and molecular dynamics simulation to identify possible inhibitors.",
            source="openalex",
            date="2026-06-11",
        )
        self.assertGreater(score_paper(method, self.topics, self.ranking), score_paper(routine, self.topics, self.ranking))

    def test_banned_fallback_phrases_fail_final_report_validation(self):
        text = "# Daily Paper Radar\n\nThis paper appears relevant to ai_drug_discovery."
        result = validate_final_report(text, candidates_available=10)
        self.assertFalse(result.ok)
        self.assertTrue(any("banned" in error.lower() for error in result.errors))

    def test_fallback_summary_is_not_valid_final_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = Paper(title="A Test Paper", source="arxiv", date="2026-06-11")
            paper.summary = fallback_summary(paper)
            stats = RunStats(raw_candidates=10, deduplicated_candidates=10, filtered_candidates=10)
            path = write_daily_report([paper], stats, "2026-06-12", Path(tmp), top_k=1)
            result = validate_final_report(path.read_text(), candidates_available=1)
            self.assertFalse(result.ok)

    def test_candidate_generation_outputs_without_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            paper = Paper(
                title="Discrete Flow Matching Candidate",
                abstract="We propose a new flow matching method for molecular generation.",
                source="arxiv",
                date="2026-06-11",
                topic_tags=["flow_matching_and_diffusion"],
            )
            score_paper(paper, self.topics, self.ranking)
            stats = RunStats(raw_candidates=1, deduplicated_candidates=1, filtered_candidates=1)
            json_path = write_candidate_json([paper], stats, "2026-06-12", repo_root)
            md_path = write_candidate_markdown([paper], stats, "2026-06-12", repo_root)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("abstract", json_path.read_text())
            self.assertIn("not a final daily report", md_path.read_text())

    def test_empty_primary_fetch_is_operational_failure(self):
        with self.assertRaisesRegex(RuntimeError, "No raw candidates"):
            require_raw_candidates([], ["arxiv", "openalex"])

    def test_banned_phrase_list_contains_degraded_language(self):
        self.assertIn("The current degraded-mode summarizer", BANNED_FINAL_REPORT_PHRASES)


if __name__ == "__main__":
    unittest.main()
