#!/usr/bin/env python3
"""
sloth_box.py - findbox
Drop it in. Forget it. Find it by what you remember.

A 100% local, standard-library tool powered by open-weight Gemma via Ollama.
Runs at idle CPU priority (os.nice(19)) to organize digital messes, extract tasks,
generate digests, and enable vague-memory search via SQLite FTS5.
"""

import argparse
import os
import sys

# Ensure module path is accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sloth_box.config import DEFAULT_MODEL, get_auto_scan_dirs
from sloth_box.organizer import run_intake, run_undo
from sloth_box.server import run_server
from sloth_box.stats import run_stats


def set_idle_priority():
    """Throttle process to lowest CPU priority (sloth mode: os.nice(19))."""
    try:
        if hasattr(os, "nice"):
            os.nice(19)
    except Exception:
        pass


def main():
    set_idle_priority()
    parser = argparse.ArgumentParser(
        description="findbox (SlothBox) • Drop it in. Forget it. Find it by what you remember."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # ── run ──────────────────────────────────────────────────────
    p_run = subparsers.add_parser(
        "run",
        help="Scan & organize files. No --inbox = auto-scan Downloads, Desktop, Documents, Screenshots…"
    )
    p_run.add_argument(
        "--inbox",
        type=str,
        nargs="+",
        metavar="PATH",
        help=(
            "One or more source folders to scan. "
            "Omit entirely for zero-config auto-scan of all common device folders "
            "(~/Downloads, ~/Desktop, ~/Documents, ~/Pictures/Screenshots, etc.)."
        )
    )
    p_run.add_argument(
        "--target",
        type=str,
        help="Destination sorted folder (default: ~/SlothBox/sorted)"
    )
    p_run.add_argument(
        "--apply",
        action="store_true",
        help="Execute actual file moves (default is dry-run — safe to run first)"
    )
    p_run.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})"
    )

    # ── undo ─────────────────────────────────────────────────────
    subparsers.add_parser("undo", help="Restore all moved files back to their original locations")

    # ── stats ────────────────────────────────────────────────────
    subparsers.add_parser("stats", help="Display the Payoff meter and laziness statistics")

    # ── serve ────────────────────────────────────────────────────
    p_serve = subparsers.add_parser("serve", help="Launch the local 127.0.0.1 web search interface")
    p_serve.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")

    args = parser.parse_args()

    if args.subcommand == "run":
        if not args.inbox:
            # Zero-config: show user what will be scanned before running
            dirs = get_auto_scan_dirs()
            if dirs:
                print("🦥 Auto-scan mode — will scan these folders on your device:")
                for d in dirs:
                    print(f"   📂 {d}")
                print()
        run_intake(
            inbox_dirs=args.inbox,   # None = auto-scan
            target_dir=args.target,
            apply=args.apply,
            model=args.model,
        )
    elif args.subcommand == "undo":
        run_undo()
    elif args.subcommand == "stats":
        run_stats()
    elif args.subcommand == "serve":
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
