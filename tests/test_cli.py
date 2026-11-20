"""Integration tests: exercise the compiled C++ executable against disposable CSV files."""
from __future__ import annotations

import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [ROOT / "build" / "assetops", ROOT / "build" / "assetops.exe",
              ROOT / "build" / "Debug" / "assetops.exe", ROOT / "build" / "Release" / "assetops.exe"]
BIN = next((p for p in CANDIDATES if p.exists()), None)


@unittest.skipIf(BIN is None, "Build C++ executable first: cmake -S . -B build && cmake --build build")
class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "assets.csv"
        shutil.copy(ROOT / "data" / "assets.csv", self.file)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args: str, ok: bool = True):
        result = subprocess.run([str(BIN), *args, "--file", str(self.file)],
                                cwd=ROOT, text=True, capture_output=True)
        if ok:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_summary_categories(self):
        out = self.run_cli("summary", "--as-of", "2026-11-19").stdout
        self.assertIn("Assets:    12", out)
        self.assertIn("Overdue:   3", out)
        self.assertIn("Due soon:  4", out)
        self.assertIn("OK:        5", out)

    def test_list_and_due(self):
        out = self.run_cli("list").stdout
        self.assertIn("A001", out)
        self.assertIn("OVERDUE", out)
        due = self.run_cli("due").stdout
        self.assertIn("Total: 7 asset(s)", due)
        self.assertNotIn("A009", due)

    def test_export_valid_csv(self):
        report = Path(self.tmp.name) / "report.csv"
        self.run_cli("export", "--output", str(report))
        with report.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(12, len(rows))
        self.assertIn("status", rows[0])
        self.assertEqual("OVERDUE", next(r for r in rows if r["id"] == "A001")["status"])

    def test_add_with_comma_and_quote(self):
        self.run_cli("add", "--id", "NEW1", "--name", 'Pump, "West"', "--category", "Water",
                     "--last-serviced", "2026-11-01", "--interval-days", "60",
                     "--hours-used", "10", "--hour-limit", "150")
        with self.file.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual('Pump, "West"', next(x for x in rows if x["id"] == "NEW1")["name"])
        duplicate = self.run_cli("add", "--id", "NEW1", "--name", "X", "--category", "Water",
                                 "--last-serviced", "2026-11-01", "--interval-days", "60",
                                 "--hours-used", "10", "--hour-limit", "150", ok=False)
        self.assertNotEqual(0, duplicate.returncode)
        self.assertIn("already exists", duplicate.stderr)

    def test_service_resets_hours(self):
        self.run_cli("service", "A001", "--date", "2026-11-19")
        with self.file.open(newline="", encoding="utf-8") as f:
            row = next(r for r in csv.DictReader(f) if r["id"] == "A001")
        self.assertEqual("2026-11-19", row["last_serviced"])
        self.assertEqual("0", row["hours_since_service"])
        self.assertIn("OK:        6", self.run_cli("summary").stdout)

    def test_rejects_invalid_date_without_mutating_file(self):
        before = self.file.read_bytes()
        result = self.run_cli("service", "A001", "--date", "2026-02-30", ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.file.read_bytes())


if __name__ == "__main__":
    unittest.main()
