"""
Unit tests for sloth_box
"""

import os
import pathlib
import shutil
import tempfile
import unittest

from sloth_box.db import get_db_connection
from sloth_box.extractor import compute_sha256, extract_docx_text, fallback_heuristics
from sloth_box.organizer import get_target_path, run_intake, run_undo, search_documents
from sloth_box.stats import compute_stats


class TestSlothBox(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="sloth_test_")
        os.environ["SLOTH_HOME"] = self.test_dir
        self.inbox = pathlib.Path(self.test_dir) / "inbox"
        self.inbox.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_heuristics_categorization(self):
        # Bill
        bill_path = pathlib.Path("sample_data/01_electricity_bill_WBSEDCL.txt")
        if bill_path.exists():
            meta = fallback_heuristics(bill_path, bill_path.read_text())
            self.assertEqual(meta["category"], "bills")
            self.assertEqual(meta["issuer_or_person"], "WBSEDCL")

        # Recipe
        recipe_path = pathlib.Path("sample_data/04_instagram_recipe_paneer_tikka.txt")
        if recipe_path.exists():
            meta = fallback_heuristics(recipe_path, recipe_path.read_text())
            self.assertEqual(meta["category"], "recipes")

        # Chat
        chat_path = pathlib.Path("sample_data/03_whatsapp_chat_flat_rent_advance.txt")
        if chat_path.exists():
            meta = fallback_heuristics(chat_path, chat_path.read_text())
            self.assertEqual(meta["category"], "chats")

    def test_safe_moves_and_undo(self):
        # Create a sample file in inbox
        dummy_file = self.inbox / "dummy_bill.txt"
        dummy_file.write_text("Electricity invoice due 2026-10-28 for WBSEDCL power consumption ₹450")

        # Run with apply
        processed = run_intake(inbox_dirs=[str(self.inbox)], apply=True)
        self.assertEqual(len(processed), 1)
        self.assertFalse(dummy_file.exists())  # moved

        # Check DB
        conn = get_db_connection()
        doc = conn.execute("SELECT * FROM documents").fetchone()
        self.assertIsNotNone(doc)
        self.assertEqual(doc["category"], "bills")

        # Check Search
        q_info, results = search_documents(conn, "electricity bill")
        self.assertTrue(len(results) >= 1)

        # Run Undo
        restored = run_undo()
        self.assertEqual(restored, 1)
        self.assertTrue(dummy_file.exists())  # safely restored

    def test_stats_payoff(self):
        dummy_file = self.inbox / "receipt_swiggy.txt"
        dummy_file.write_text("Swiggy instamart order receipt ₹350")
        run_intake(inbox_dirs=[str(self.inbox)], apply=True)

        st = compute_stats()
        self.assertEqual(st["files_indexed"], 1)
        self.assertEqual(st["user_effort_minutes"], 0)
        self.assertGreater(st["minutes_saved"], 0)


if __name__ == "__main__":
    unittest.main()
