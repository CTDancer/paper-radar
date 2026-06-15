import unittest

from paper_radar.config import load_all_configs, load_config


class ConfigTests(unittest.TestCase):
    def test_config_loading_works(self):
        topics = load_config("topics.yaml")
        self.assertIn("topic_groups", topics)
        all_configs = load_all_configs()
        self.assertIn("ranking", all_configs)
        self.assertIn("sources", all_configs)


if __name__ == "__main__":
    unittest.main()
