"""
Unit tests for search engine: FTS5 escaping, BM25 ranking, and natural query filtering.
"""

import os
import pathlib
import shutil
import tempfile
import unittest

from sloth_box.db import escape_fts5_query, get_db_connection, index_document
from sloth_box.organizer import search_documents


class TestSearchEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="sloth_search_")
        os.environ["SLOTH_HOME"] = self.test_dir
        self.conn = get_db_connection()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fts5_query_escaping(self):
        # Malformed queries with special characters that would crash raw FTS5
        q1 = escape_fts5_query('recipe: "paneer"* AND (NOT sweet)')
        self.assertNotIn("(", q1)
        self.assertNotIn(")", q1)
        self.assertNotIn("*", q1)

        # Single quote attack
        q2 = escape_fts5_query("test' OR 1=1--")
        self.assertTrue(len(q2) > 0)

    def test_bm25_and_date_filtering(self):
        # Index two test documents
        doc1 = {
            "file_hash": "hash1",
            "original_path": "/tmp/doc1.txt",
            "current_path": "/tmp/doc1.txt",
            "filename": "2026-09-04_paneer_tikka_recipe.txt",
            "category": "recipes",
            "document_date": "2026-09-04",
            "title": "paneer-tikka-recipe",
            "issuer_or_person": "Instagram",
            "summary": "Restaurant style smoky paneer tikka recipe",
            "readable_text": "Ingredients 300g paneer yogurt spices",
            "app": "Instagram",
            "tags": "recipes paneer cooking dinner",
            "todos": [],
            "amounts": []
        }
        doc2 = {
            "file_hash": "hash2",
            "original_path": "/tmp/doc2.txt",
            "current_path": "/tmp/doc2.txt",
            "filename": "2026-10-12_electricity_bill_wbsedcl.txt",
            "category": "bills",
            "document_date": "2026-10-12",
            "title": "electricity-bill-wbsedcl",
            "issuer_or_person": "WBSEDCL",
            "summary": "Electricity invoice for power consumption",
            "readable_text": "Consumer ID units 370 kWh gross due 2555",
            "app": "",
            "tags": "bills electricity power wbsedcl",
            "todos": [{"task": "Pay bill by 2026-10-28", "deadline_or_empty": "2026-10-28"}],
            "amounts": ["2555.50"]
        }
        index_document(self.conn, doc1)
        index_document(self.conn, doc2)

        # Search for recipe
        q_info, results = search_documents(self.conn, "paneer recipe")
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["category"], "recipes")

        # Search for bill
        q_info_bill, results_bill = search_documents(self.conn, "wbsedcl power bill")
        self.assertTrue(len(results_bill) >= 1)
        self.assertEqual(results_bill[0]["category"], "bills")


if __name__ == "__main__":
    unittest.main()
