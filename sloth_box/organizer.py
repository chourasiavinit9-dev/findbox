"""
sloth_box.organizer
File organization, collision avoidance, atomic moves, TODO & Digest generation,
and safe transactional undo.
"""

import datetime
import json
import pathlib
import re
import shutil
from .ai import analyze_file_with_gemma, parse_vague_query
from .config import BASE_DIR, DIGEST_PATH, TODO_PATH, get_auto_scan_dirs
from .db import escape_fts5_query, get_db_connection, index_document, log_move
from .errors import SecurityViolationError
from .extractor import compute_sha256, extract_content
from .security import QUERY_CACHE, fnv1a32, sanitize_filename


def get_target_path(target_base: pathlib.Path, category: str, doc_date: str, title: str, issuer: str, ext: str) -> pathlib.Path:
    """Computes target path with strict path traversal immunity and collision resolution."""
    if ".." in category or "/" in category or "\\" in category:
        raise SecurityViolationError(f"Attempted path traversal in category name: {category}")

    # Enforce safe category
    safe_cat = sanitize_filename(category)
    cat_dir = (target_base / safe_cat).resolve()

    # Security check: Ensure cat_dir is strictly inside target_base
    if not str(cat_dir).startswith(str(target_base.resolve())):
        raise SecurityViolationError(f"Attempted path traversal outside target directory: {cat_dir}")

    cat_dir.mkdir(parents=True, exist_ok=True)

    clean_title = sanitize_filename(title)
    clean_issuer = sanitize_filename(issuer) if issuer and issuer.lower() != "unknown" else ""

    if clean_issuer:
        base_name = f"{doc_date}_{clean_title}_{clean_issuer}"
    else:
        base_name = f"{doc_date}_{clean_title}"

    clean_ext = sanitize_filename(ext)
    if not clean_ext.startswith(".") and clean_ext:
        clean_ext = f".{clean_ext}"

    target = cat_dir / f"{base_name}{clean_ext}"
    counter = 1
    while target.exists():
        target = cat_dir / f"{base_name}-{counter}{clean_ext}"
        counter += 1
    return target


def update_todo_file(all_todos):
    """Generates TODO.md sorted by deadline, grouping 'Due soon' (<7 days)."""
    if not all_todos:
        return

    today = datetime.date.today()
    due_soon = []
    upcoming = []
    no_deadline = []

    for t in all_todos:
        d_str = t.get("deadline_or_empty")
        if d_str:
            try:
                d_obj = datetime.date.fromisoformat(d_str)
                delta = (d_obj - today).days
                if delta <= 7:
                    due_soon.append((d_obj, t))
                else:
                    upcoming.append((d_obj, t))
                continue
            except Exception:
                pass
        no_deadline.append(t)

    due_soon.sort(key=lambda x: x[0])
    upcoming.sort(key=lambda x: x[0])

    lines = [
        "# SlothBox Action Items & Deadlines\n",
        f"*Generated automatically on {today.isoformat()} while you rested.*\n\n"
    ]

    if due_soon:
        lines.append("## 🚨 Due Soon (Next 7 Days)\n")
        for d_obj, t in due_soon:
            lines.append(f"- [ ] **Due {d_obj.isoformat()}**: {t['task']} (`{t['filename']}`)\n")
        lines.append("\n")

    if upcoming:
        lines.append("## 📅 Upcoming Deadlines\n")
        for d_obj, t in upcoming:
            lines.append(f"- [ ] Due {d_obj.isoformat()}: {t['task']} (`{t['filename']}`)\n")
        lines.append("\n")

    if no_deadline:
        lines.append("## 📌 Other Action Items\n")
        for t in no_deadline:
            lines.append(f"- [ ] {t['task']} (`{t['filename']}`)\n")
        lines.append("\n")

    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def append_digest(processed_items, dry_run=False):
    """Appends run summary to digest.md ('While you did nothing')."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_str = "DRY-RUN (Simulated)" if dry_run else "EXECUTED"

    lines = [
        f"\n## Run: {now_str} [{mode_str}]\n\n",
        f"**Files Processed:** {len(processed_items)}\n\n"
    ]

    if not processed_items:
        lines.append("No new files found in inbox. Inbox is clean.\n")
    else:
        lines.append("### Organized Files\n")
        for item in processed_items:
            status = "Planned Move" if dry_run else "Moved"
            lines.append(f"- **{status}**: `{item['src'].name}` ➔ `{item['dst'].relative_to(BASE_DIR)}`\n")
            lines.append(f"  *Summary*: {item['meta'].get('one_sentence_summary', '')}\n")

        all_todos = [t for item in processed_items for t in item["meta"].get("todos", [])]
        if all_todos:
            lines.append("\n### New Tasks Discovered\n")
            for t in all_todos:
                dl = f" (Deadline: {t['deadline_or_empty']})" if t.get("deadline_or_empty") else ""
                lines.append(f"- [ ] {t['task']}{dl}\n")

    with open(DIGEST_PATH, "a", encoding="utf-8") as f:
        f.writelines(lines)


def run_intake(inbox_dirs=None, target_dir=None, apply=False, model=None):
    """
    Performs full intake scan across one or more folders.
    If inbox_dirs is None or empty, auto-discovers all common device
    landfill folders (Downloads, Desktop, Documents, Screenshots, etc.)
    so the user never has to specify a path — true zero-config lazy mode.
    """
    from .ai import DEFAULT_MODEL
    active_model = model or DEFAULT_MODEL

    conn = get_db_connection()
    target_base = pathlib.Path(target_dir or (BASE_DIR / "sorted")).resolve()
    target_base.mkdir(parents=True, exist_ok=True)

    # ── Resolve which folders to scan ──────────────────────────
    if inbox_dirs:
        # Explicit paths provided via CLI
        scan_paths = [pathlib.Path(d).resolve() for d in inbox_dirs]
        scan_paths = [p for p in scan_paths if p.exists() and p.is_dir()]
        source_label = "explicit"
    else:
        # Zero-config: scan every common messy folder on the device
        scan_paths = get_auto_scan_dirs()
        source_label = "auto-discovered"

    if not scan_paths:
        print("⚠️  No valid folders found to scan. Use --inbox to specify a path.")
        return []

    print("🦥 SlothBox Intake — ZERO CONFIG MODE")
    print(f"   Source:  {source_label} ({len(scan_paths)} folder(s))")
    for sp in scan_paths:
        print(f"            📂 {sp}")
    print(f"   Target:  {target_base}")
    print(f"   Mode:    {'🚀 APPLY (Executing moves)' if apply else '🔍 DRY-RUN (planning only — add --apply to execute)'}")
    print(f"   Model:   {active_model} (100% local, idle CPU priority)\n")

    # ── Collect all files across all scan paths ────────────────
    SUPPORTED_EXTS = {
        ".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".log",
        ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    }
    all_files = []
    seen_paths = set()
    for folder in scan_paths:
        # Skip if this folder is inside target_base (prevent re-ingesting sorted files)
        try:
            folder.relative_to(target_base)
            continue  # it's a subfolder of target — skip
        except ValueError:
            pass
        for p in folder.iterdir():
            key = str(p.resolve())
            if (
                p.is_file()
                and not p.name.startswith(".")
                and p.suffix.lower() in SUPPORTED_EXTS
                and key not in seen_paths
            ):
                seen_paths.add(key)
                all_files.append(p)

    if not all_files:
        print("✅ All scanned folders are already clean — nothing new to organize!")
        append_digest([], dry_run=not apply)
        return []

    print(f"Found {len(all_files)} file(s) across {len(scan_paths)} folder(s).\n")

    processed_items = []
    all_accumulated_todos = []

    for idx, filepath in enumerate(all_files, 1):
        print(f"[{idx}/{len(all_files)}] Reading: {filepath.name}  (from {filepath.parent.name}/)")
        try:
            fhash = compute_sha256(filepath)
        except Exception as e:
            print(f"       ⚠️  Could not read {filepath.name}: {e} — skipping.")
            continue

        row = conn.execute("SELECT * FROM documents WHERE file_hash = ?", (fhash,)).fetchone()
        if row and row["current_path"] and pathlib.Path(row["current_path"]).exists():
            print(f"       → Already indexed as {pathlib.Path(row['current_path']).name}. Skipping.")
            continue

        try:
            extracted = extract_content(filepath)
        except Exception as e:
            print(f"       ⚠️  Extraction failed for {filepath.name}: {e} — skipping.")
            continue

        meta = analyze_file_with_gemma(filepath, extracted, model=active_model)

        target_path = get_target_path(
            target_base,
            meta.get("category", "other"),
            meta.get("document_date", "nodate"),
            meta.get("title", "untitled"),
            meta.get("issuer_or_person", ""),
            filepath.suffix.lower()
        )

        print(f"       Category:  {meta.get('category')} | Date: {meta.get('document_date')}")
        print(f"       Summary:   {meta.get('one_sentence_summary')}")
        if meta.get("todos"):
            for td in meta["todos"]:
                print(f"       ✓ Task:    {td['task']} (Due: {td.get('deadline_or_empty', 'none')})")

        doc_record = {
            "file_hash": fhash,
            "original_path": str(filepath),
            "current_path": str(target_path if apply else filepath),
            "filename": target_path.name if apply else filepath.name,
            "category": meta.get("category", "other"),
            "document_date": meta.get("document_date", ""),
            "title": meta.get("title", filepath.stem),
            "issuer_or_person": meta.get("issuer_or_person", ""),
            "summary": meta.get("one_sentence_summary", ""),
            "readable_text": meta.get("readable_text", ""),
            "app": meta.get("app", ""),
            "tags": " ".join(meta.get("search_tags", [])),
            "todos": meta.get("todos", []),
            "amounts": meta.get("amounts", [])
        }

        if apply:
            shutil.move(str(filepath), str(target_path))
            log_move(conn, fhash, filepath, target_path)
            index_document(conn, doc_record)
        else:
            index_document(conn, doc_record)

        processed_items.append({"src": filepath, "dst": target_path, "meta": meta})

        for t in meta.get("todos", []):
            all_accumulated_todos.append({
                "task": t.get("task", ""),
                "deadline_or_empty": t.get("deadline_or_empty", ""),
                "filename": target_path.name
            })

    if all_accumulated_todos:
        rows = conn.execute("SELECT filename, todos_json FROM documents WHERE todos_json != '[]'").fetchall()
        db_todos = []
        for r in rows:
            tds = json.loads(r["todos_json"])
            for td in tds:
                db_todos.append({"task": td.get("task"), "deadline_or_empty": td.get("deadline_or_empty"), "filename": r["filename"]})
        update_todo_file(db_todos)

    QUERY_CACHE.clear()
    append_digest(processed_items, dry_run=not apply)

    print("\n" + "=" * 60)
    if apply:
        print(f"🎉 Done! {len(processed_items)} files organized, moved, and indexed.")
        print(f"   TODO updated:   {TODO_PATH}")
        print(f"   Digest updated: {DIGEST_PATH}")
    else:
        print(f"🔎 Dry-run: {len(processed_items)} files planned. No files moved yet.")
        print(f"   Re-run with --apply to execute: python3 sloth_box.py run --apply")
    print("=" * 60 + "\n")
    return processed_items


def run_undo():
    """Safely restores all moved files back to original positions."""
    conn = get_db_connection()
    moves = conn.execute("SELECT * FROM moves_log WHERE undone = 0 ORDER BY id DESC").fetchall()
    if not moves:
        print("No moves to undo!")
        return 0

    print(f"Restoring {len(moves)} moved files to their original locations...")
    restored = 0
    for m in moves:
        src = pathlib.Path(m["target_path"])
        dst = pathlib.Path(m["source_path"])
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            with conn:
                conn.execute("UPDATE moves_log SET undone = 1 WHERE id = ?", (m["id"],))
                conn.execute("UPDATE documents SET current_path = ?, filename = ? WHERE file_hash = ?", (str(dst), dst.name, m["file_hash"]))
            restored += 1
            print(f" ✓ Restored: {src.name} -> {dst}")
        else:
            print(f" ⚠️ Missing file {src}, skipping.")

    QUERY_CACHE.clear()
    print(f"\nUndo complete: {restored} files restored safely.")
    return restored


def search_documents(conn, natural_query: str):
    """Executes FTS5 bm25 search with microsecond FNV-1a LRU caching."""
    cache_key = fnv1a32(natural_query)
    cached = QUERY_CACHE.get(cache_key)
    if cached is not None:
        return cached

    query_info = parse_vague_query(natural_query)
    keywords = query_info.get("keywords", [])
    cat_hint = query_info.get("category_hint", "")
    d_from = query_info.get("date_from", "")
    d_to = query_info.get("date_to", "")

    with conn:
        conn.execute("UPDATE stats_counters SET searches_count = searches_count + 1 WHERE id = 1")

    results = []
    fts_clause = escape_fts5_query(" ".join(keywords))

    if fts_clause:
        try:
            sql = """
                SELECT d.*, bm25(documents_fts) as rank
                FROM documents_fts f
                JOIN documents d ON f.rowid = d.id
                WHERE documents_fts MATCH ?
            """
            params = [fts_clause]
            if cat_hint:
                sql += " AND d.category = ?"
                params.append(cat_hint)
            if d_from and d_to:
                sql += " AND d.document_date BETWEEN ? AND ?"
                params.extend([d_from, d_to])
            sql += " ORDER BY rank LIMIT 25"
            rows = conn.execute(sql, params).fetchall()
            results = [dict(r) for r in rows]
        except Exception:
            results = []

    if not results and (d_from or cat_hint or keywords):
        sql = "SELECT * FROM documents WHERE 1=1"
        params = []
        if cat_hint:
            sql += " AND category = ?"
            params.append(cat_hint)
        if d_from and d_to:
            sql += " AND document_date BETWEEN ? AND ?"
            params.extend([d_from, d_to])
        sql += " ORDER BY document_date DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
        results = [dict(r) for r in rows]

    response = (query_info, results)
    QUERY_CACHE.set(cache_key, response)
    return response
