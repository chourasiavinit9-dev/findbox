"""
Unit tests for security, sanitization, XSS disarming, and binary magic-byte detection.
"""

import pathlib
import tempfile
import unittest
from sloth_box.errors import SecurityViolationError
from sloth_box.organizer import get_target_path
from sloth_box.security import (
    check_executable_magic_bytes,
    disarm_xss,
    fnv1a32,
    sanitize_filename,
)


class TestSecurityDefenses(unittest.TestCase):
    def test_path_traversal_sanitization(self):
        # Direct path traversal strings (os.path.basename strips directory path)
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\windows\\system32\\cmd.exe"), "cmd.exe")
        self.assertEqual(sanitize_filename("valid_file.pdf"), "valid_file.pdf")
        self.assertEqual(sanitize_filename(""), "untitled-item")
        self.assertEqual(sanitize_filename("CON.txt"), "file_CON.txt")

    def test_target_path_enforcement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = pathlib.Path(tmpdir).resolve()
            # Normal target creation
            target = get_target_path(base, "bills", "2026-10-12", "electric-bill", "wbsedcl", ".txt")
            self.assertTrue(str(target).startswith(str(base)))

            # Attempt path traversal via category
            with self.assertRaises(SecurityViolationError):
                get_target_path(base, "../../../etc", "2026-10-12", "exploit", "none", ".txt")

    def test_xss_disarming(self):
        raw_xss = '<script>alert("hacked")</script><b>Hello</b>'
        disarmed = disarm_xss(raw_xss)
        self.assertNotIn("<script>", disarmed)
        self.assertIn("&lt;b&gt;Hello&lt;/b&gt;", disarmed)

        iframe_xss = '<iframe src="javascript:alert(1)"></iframe>'
        disarmed_iframe = disarm_xss(iframe_xss)
        self.assertNotIn("<iframe", disarmed_iframe)

        inline_xss = '<img src="x" onerror="alert(1)">'
        disarmed_inline = disarm_xss(inline_xss)
        self.assertNotIn("onerror", disarmed_inline)

    def test_executable_magic_bytes_quarantine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir)

            # Linux ELF binary
            elf_file = p / "malicious_script"
            elf_file.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            self.assertTrue(check_executable_magic_bytes(elf_file))

            # Windows PE binary (.exe)
            pe_file = p / "trojan.exe"
            pe_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")
            self.assertTrue(check_executable_magic_bytes(pe_file))

            # Normal text file
            txt_file = p / "safe_document.txt"
            txt_file.write_text("This is an ordinary electricity bill text.")
            self.assertFalse(check_executable_magic_bytes(txt_file))

    def test_fnv1a32_hashing(self):
        h1 = fnv1a32("test query")
        h2 = fnv1a32("test query")
        h3 = fnv1a32("different query")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 8)


if __name__ == "__main__":
    unittest.main()
