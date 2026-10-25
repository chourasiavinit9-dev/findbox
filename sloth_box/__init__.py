"""
sloth_box package
findbox - Drop it in. Forget it. Find it by what you remember.
"""

from .config import BASE_DIR, DEFAULT_MODEL, OLLAMA_API_BASE
from .organizer import run_intake, run_undo, search_documents
from .server import run_server
from .stats import compute_stats, run_stats

__all__ = [
    "run_intake",
    "run_undo",
    "run_stats",
    "run_server",
    "search_documents",
    "compute_stats",
    "BASE_DIR",
    "DEFAULT_MODEL",
    "OLLAMA_API_BASE"
]
