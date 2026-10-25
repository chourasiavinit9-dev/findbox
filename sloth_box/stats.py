"""
sloth_box.stats
Payoff Meter metrics, laziness calculations, and benchmark assumptions.
"""

import json
from .config import MINUTES_PER_FILE, MINUTES_PER_SEARCH
from .db import get_db_connection


def compute_stats():
    """Computes exact metrics for the Payoff Meter."""
    conn = get_db_connection()
    doc_count = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()["cnt"]
    moves_count = conn.execute("SELECT COUNT(*) as cnt FROM moves_log WHERE undone = 0").fetchone()["cnt"]

    rows = conn.execute("SELECT todos_json FROM documents").fetchall()
    todo_count = sum(len(json.loads(r["todos_json"])) for r in rows if r["todos_json"])

    search_row = conn.execute("SELECT searches_count FROM stats_counters WHERE id = 1").fetchone()
    search_count = search_row["searches_count"] if search_row else 0

    minutes_saved = (doc_count * MINUTES_PER_FILE) + (search_count * MINUTES_PER_SEARCH)

    return {
        "files_indexed": doc_count,
        "files_moved": moves_count,
        "tasks_extracted": todo_count,
        "searches_performed": search_count,
        "minutes_saved": round(minutes_saved, 1),
        "user_effort_minutes": 0
    }


def run_stats():
    """Prints formatted Payoff statistics in the terminal."""
    st = compute_stats()
    print("=" * 55)
    print("🦥 SLOTHBOX PAYOFF METER")
    print("=" * 55)
    print(f"  Files Indexed:             {st['files_indexed']}")
    print(f"  Files Organized & Moved:   {st['files_moved']}")
    print(f"  Action Items Extracted:    {st['tasks_extracted']}")
    print(f"  Vague Searches Handled:    {st['searches_performed']}")
    print("-" * 55)
    print(f"  Estimated Time Saved:      {st['minutes_saved']} minutes")
    print(f"  Your Effort:               {st['user_effort_minutes']} minutes (100% laziness)")
    print("=" * 55)
    print("Assumptions: ~1.5 min per manual file sort + 5.0 min per search avoided.")
    print("All processing was performed locally with zero cloud API spend.\n")
    return st
