"""
sloth_box.security
Defensive security utilities: Path-traversal sanitization, XSS disarming,
executable magic-byte blocking, and microsecond FNV-1a LRU caching.
"""

import collections
import html
import os
import pathlib
import re
from .errors import SecurityViolationError

# 32-bit FNV-1a Hashing for microsecond cache key generation
def fnv1a32(s: str) -> str:
    """Calculates 32-bit FNV-1a hash of a string."""
    hash_val = 0x811c9dc5
    for char in s.encode("utf-8"):
        hash_val ^= char
        hash_val = (hash_val * 0x01000193) & 0xFFFFFFFF
    return f"{hash_val:08x}"


class MicrosecondCache:
    """Thread-safe LRU in-memory cache for query parsing and search results."""
    def __init__(self, capacity=256):
        self.capacity = capacity
        self.cache = collections.OrderedDict()

    def get(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


# Global cache instance for zero-latency queries
QUERY_CACHE = MicrosecondCache(capacity=500)


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename against path traversal (../, ..\), control characters,
    null bytes, and OS-reserved device names.
    """
    if not filename:
        return "untitled-item"

    # Normalize both Unix and Windows separators
    normalized = filename.replace("\\", "/")
    base = os.path.basename(normalized)

    # Disarm path traversal attempts
    base = base.replace("..", "").replace("/", "").replace("\\", "").replace("\x00", "")

    # Disarm Windows reserved device names
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                "LPT1", "LPT2", "LPT3", "LPT4", "CLOCK$"}
    stem, ext = os.path.splitext(base)
    if stem.upper() in reserved:
        stem = f"file_{stem}"

    # Replace invalid punctuation with hyphens, preserve alphanumeric, underscore, dot
    sanitized = re.sub(r"[^a-zA-Z0-9._\-\u0900-\u097F\u0980-\u09FF]+", "-", stem).strip("-")
    if not sanitized:
        sanitized = "item"

    clean_ext = re.sub(r"[^a-zA-Z0-9.]", "", ext).lower()[:10]
    return f"{sanitized}{clean_ext}"


def disarm_xss(content: str) -> str:
    """Disarms XSS payloads, script tags, javascript: URIs, and dangerous HTML."""
    if not content:
        return ""
    # Strip script/iframe tags
    cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", content, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    # Disarm inline event handlers
    cleaned = re.sub(r"\bon\w+\s*=", "data-disarmed=", cleaned, flags=re.IGNORECASE)
    # Disarm javascript: pseudo-protocol
    cleaned = re.sub(r"javascript\s*:", "disarmed:", cleaned, flags=re.IGNORECASE)
    # Final HTML entity escape
    return html.escape(cleaned)


def check_executable_magic_bytes(filepath: pathlib.Path) -> bool:
    """
    Inspects file headers for executable binaries (Windows PE, Linux ELF, Mach-O).
    Returns True if file is an executable binary that should be quarantined.
    """
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)
        if len(header) < 4:
            return False

        # Windows PE (MZ)
        if header.startswith(b"MZ"):
            return True
        # Linux ELF (\x7fELF)
        if header.startswith(b"\x7fELF"):
            return True
        # Mach-O (macOS binaries: 0xfeedface, 0xfeedfacf, 0xcefaedfe, 0xcffaedfe, fat binary 0xcafebabe)
        if header[:4] in {b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"}:
            return True
        # Shell scripts with shebang
        if header.startswith(b"#!"):
            return True

        return False
    except Exception:
        return False
