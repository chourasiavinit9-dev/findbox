"""
Unit tests for Payoff Meter and laziness statistics calculations.
"""

import os
import pathlib
import shutil
import tempfile
import unittest

from sloth_box.config import MINUTES_PER_FILE, MINUTES_PER_SEARCH
from sloth_box.organizer import run_intake
from sloth_box.stats import compute_stats


class TestStats(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="sloth_stats_")
        os.environ["SLOTH_HOME"] = self.test_dir
        self.inbox = pathlib.Path(self.test_dir) / "inbox"
        self.inbox.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_payoff_formula_constants(self):
        self.assertEqual(MINUTES_PER_FILE, 1.5)
        self.assertEqual(MINUTES_PER_SEARCH, 5.0)

    def test_zero_effort_invariant(self):
        st = compute_stats()
        self.assertEqual(st["user_effort_minutes"], 0)

    def test_payoff_scaling(self):
        for i in range(3):
            f = self.inbox / f"file_{i}.txt"
            f.write_text(f"Note {i}")

        run_intake(inbox_dirs=[str(self.inbox)], apply=True)
        st = compute_stats()
        self.assertEqual(st["files_indexed"], 3)
        self.assertEqual(st["minutes_saved"], round(3 * 1.5, 1))
        self.assertEqual(st["user_effort_minutes"], 0)


if __name__ == "__main__":
    unittest.main()
