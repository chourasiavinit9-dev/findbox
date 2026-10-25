"""
sloth_box.config
Centralized configuration, paths, and constants.
"""

import os
import pathlib

# Environment-configurable model & API base
DEFAULT_MODEL = os.environ.get("SLOTH_MODEL", os.environ.get("OLLAMA_MODEL", "gemma3:4b"))
OLLAMA_API_BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

def get_base_dir():
    return pathlib.Path(os.environ.get("SLOTH_HOME", os.path.expanduser("~/SlothBox"))).resolve()

def get_db_path():
    return get_base_dir() / "slothbox.db"

def get_todo_path():
    return get_base_dir() / "TODO.md"

def get_digest_path():
    return get_base_dir() / "digest.md"

class _PathProxy:
    def __init__(self, getter):
        self.getter = getter
    def __str__(self):
        return str(self.getter())
    def __repr__(self):
        return repr(self.getter())
    def __fspath__(self):
        return str(self.getter())
    def __truediv__(self, other):
        return self.getter() / other
    def __getattr__(self, name):
        return getattr(self.getter(), name)

BASE_DIR   = _PathProxy(get_base_dir)
DB_PATH    = _PathProxy(get_db_path)
TODO_PATH  = _PathProxy(get_todo_path)
DIGEST_PATH = _PathProxy(get_digest_path)

# Standard Categories
CATEGORIES = [
    "bills", "receipts", "identity", "medical", "work", "study",
    "travel", "recipes", "chats", "screenshots", "photos", "forms", "other"
]

# Payoff Meter constants (honest benchmark assumptions)
MINUTES_PER_FILE   = 1.5   # Time to open, read, name, and categorize by hand
MINUTES_PER_SEARCH = 5.0   # Time wasted digging through unorganized downloads/chats

# ──────────────────────────────────────────────────────────────
# AUTO-SCAN: The device's most common digital landfill folders.
# Used when no --inbox is specified (true zero-config lazy mode).
# All paths are resolved at runtime so symlinks are followed.
# ──────────────────────────────────────────────────────────────
_HOME = os.path.expanduser("~")

AUTO_SCAN_DIRS = [
    # The classic dump zone
    os.path.join(_HOME, "Downloads"),
    # Desktop clutter
    os.path.join(_HOME, "Desktop"),
    # Screenshots — macOS default location (Cmd+Shift+3/4)
    os.path.join(_HOME, "Desktop"),           # macOS <= Sonoma default
    os.path.join(_HOME, "Pictures", "Screenshots"),   # macOS Sequoia+
    # WhatsApp / Telegram exported chats & media
    os.path.join(_HOME, "Documents", "WhatsApp Chat"),
    os.path.join(_HOME, "Documents", "Telegram Desktop"),
    # Scanned documents
    os.path.join(_HOME, "Documents", "Scanned Documents"),
    os.path.join(_HOME, "Documents", "Scans"),
    # Generic Documents overflow
    os.path.join(_HOME, "Documents"),
    # iCloud Drive local cache (common on macOS)
    os.path.join(_HOME, "Library", "Mobile Documents", "com~apple~CloudDocs", "Downloads"),
]

def get_auto_scan_dirs():
    """Returns the list of existing auto-scan directories (deduped)."""
    seen = set()
    result = []
    for raw in AUTO_SCAN_DIRS:
        p = pathlib.Path(raw).resolve()
        key = str(p)
        if key not in seen and p.exists() and p.is_dir():
            seen.add(key)
            result.append(p)
    return result
