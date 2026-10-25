"""
Unit tests for file ingestion and extractors: DOCX, PDF, corrupted files, and heuristics.
"""

import pathlib
import tempfile
import unittest
from sloth_box.extractor import (
    compute_sha256,
    extract_content,
    extract_docx_text,
    extract_pdf_text,
    fallback_heuristics,
)


class TestExtractor(unittest.TestCase):
    def test_docx_extraction(self):
        docx_path = pathlib.Path("sample_data/07_project_spec_q3_roadmap.docx")
        if docx_path.exists():
            text = extract_docx_text(docx_path)
            self.assertIn("PROJECT SPECIFICATION", text)
            self.assertIn("Gemma", text)

    def test_corrupted_file_resilience(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)
            corrupt_file = p / "corrupt.docx"
            corrupt_file.write_bytes(b"PK\x03\x04corrupted_garbage_bytes")

            # Must degrade gracefully and never crash
            extracted = extract_content(corrupt_file)
            self.assertIn(extracted["type"], ["text", "binary"])

            meta = fallback_heuristics(corrupt_file, extracted.get("text", ""))
            self.assertIsNotNone(meta["category"])
            self.assertIsNotNone(meta["title"])

    def test_sha256_computation(self):
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"deterministic content")
            tmp.flush()
            h = compute_sha256(pathlib.Path(tmp.name))
            self.assertEqual(len(h), 64)


if __name__ == "__main__":
    unittest.main()
