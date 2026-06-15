import unittest

from paper_radar.models import Paper
from paper_radar.pipeline.deduplicate import deduplicate_papers


class DeduplicateTests(unittest.TestCase):
    def test_deduplicates_by_doi(self):
        papers = [
            Paper(title="A Flow Matching Paper", doi="10.123/example", source="arxiv"),
            Paper(title="A Flow Matching Paper Extended", doi="10.123/example", source="openalex"),
        ]
        merged = deduplicate_papers(papers)
        self.assertEqual(len(merged), 1)
        self.assertIn("openalex", merged[0].source)

    def test_deduplicates_by_arxiv_id(self):
        papers = [
            Paper(title="Discrete Flow Matching", arxiv_id="2401.12345", source="arxiv"),
            Paper(title="Discrete Flow Matching", arxiv_id="2401.12345", source="semantic_scholar"),
        ]
        self.assertEqual(len(deduplicate_papers(papers)), 1)

    def test_fuzzy_title_deduplication(self):
        papers = [
            Paper(title="Flow Matching for Molecular Generation", source="arxiv"),
            Paper(title="Flow Matching for Molecular Generations", source="openalex"),
        ]
        self.assertEqual(len(deduplicate_papers(papers)), 1)


if __name__ == "__main__":
    unittest.main()
