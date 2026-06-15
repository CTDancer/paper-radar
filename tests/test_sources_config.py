import unittest

from paper_radar.config import load_config
from paper_radar.models import Paper
from paper_radar.pipeline.fetch import ENRICHERS, FETCHERS, queries_for_source, query_group_names
from paper_radar.pipeline.rank import score_paper


class SourcesConfigTests(unittest.TestCase):
    def setUp(self):
        self.sources = load_config("sources.yaml")
        self.topics = load_config("topics.yaml")
        self.ranking = load_config("ranking.yaml")

    def test_query_groups_are_source_specific(self):
        groups = self.sources["query_groups"]
        expected = {
            "ml_core",
            "optimization",
            "ai_drug_discovery",
            "molecular_glue_tpd",
            "transferable_insights",
        }
        self.assertEqual(set(groups), expected)
        self.assertEqual(set(query_group_names(self.sources)), expected)

        for name, settings in self.sources["sources"].items():
            if settings.get("mode") == "enrichment":
                continue
            selected = settings.get("query_groups", [])
            self.assertTrue(selected, f"{name} should choose source-specific query groups")
            self.assertTrue(set(selected).issubset(expected))
            self.assertTrue(queries_for_source(self.sources, settings))

    def test_configured_sources_have_fetchers_or_enrichers(self):
        for name, settings in self.sources["sources"].items():
            if not settings.get("enabled", True):
                continue
            if settings.get("mode") == "enrichment":
                self.assertIn(name, ENRICHERS)
            else:
                self.assertIn(name, FETCHERS)

    def test_arxiv_broad_discovery_is_secondary(self):
        arxiv = self.sources["sources"]["arxiv"]
        broad = arxiv["broad_discovery"]
        self.assertTrue(broad["enabled"])
        self.assertTrue(broad["secondary"])
        self.assertIn("cs.LG", broad["categories"])

    def test_ranking_does_not_reward_query_matches_directly(self):
        routine = Paper(
            title="Structure-based drug design by molecular docking for a single target",
            abstract="We apply molecular docking, virtual screening, ADMET, and molecular dynamics to prioritize inhibitors.",
            source="crossref",
            date="2026-06-11",
        )
        score_paper(routine, self.topics, self.ranking)
        self.assertEqual(routine.score_breakdown["paper_type"], "routine_application")
        self.assertEqual(routine.score_breakdown["transferable_insight"], 0.0)
        self.assertFalse(any("query" in key for key in routine.score_breakdown))
        self.assertNotEqual(routine.priority, "Must Read")


if __name__ == "__main__":
    unittest.main()
