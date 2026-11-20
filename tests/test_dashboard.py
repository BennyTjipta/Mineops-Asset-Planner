"""HTML report rendering tests: no external packages required."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import build_html


class TestDashboard(unittest.TestCase):
    def test_escape_untrusted_asset_name(self):
        row = {"id": "X1", "name": '<img src=x onerror=alert(1)>', "category": "Other",
               "last_serviced": "2026-01-01", "service_due": "2026-12-01",
               "days_remaining": "12", "hours_remaining": "20", "status": "DUE_SOON"}
        html = build_html([row], "2026-11-19")
        self.assertNotIn('<img src=x onerror=alert(1)>', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('Showing 1 assets', html)

    def test_empty_report(self):
        html = build_html([], "2026-11-19")
        self.assertIn('Total assets', html)
        self.assertIn('Showing 0 assets', html)

if __name__ == "__main__":
    unittest.main()
