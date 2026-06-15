from datetime import date
import unittest

from paper_radar.utils.dates import within_lookback


class DateTests(unittest.TestCase):
    def test_within_lookback_rejects_future_dates(self):
        today = date(2026, 6, 13)
        self.assertTrue(within_lookback("2026-06-12", 3, today=today))
        self.assertTrue(within_lookback("2026-06-13", 3, today=today))
        self.assertFalse(within_lookback("2026-06-14", 3, today=today))


if __name__ == "__main__":
    unittest.main()
