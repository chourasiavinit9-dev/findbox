"""
sloth_box.db
SQLite database management, schema creation, FTS5 full-text indexing, and audit logging.
"""

import datetime
import json
import re
import sqlite3
from .config import BASE_DIR, DB_PATH
from .errors import DatabaseError


def escape_fts5_query(query_str: str) -> str:
    """Escapes FTS5 special operators and tokens to prevent syntax errors."""
    if not query_str:
        return ""
    # Strip FTS5 operators like *, :, ^, NOT, AND, OR unless part of clean words
    clean = re.sub(r'["*^:(){}]', ' ', query_str)
    tokens = clean.split()
    escaped_tokens = []
    for t in tokens:
        if t.strip():
            clean_word = re.sub(r"[^a-zA-Z0-9_\u0900-\u097F\u0980-\u09FF]", "", t)
            if clean_word:
                escaped_tokens.append('"' + clean_word + '"')
    return " OR ".join([t for t in escaped_tokens if len(t) > 2])


def get_db_connection():
    """Returns a connected SQLite instance with WAL mode and schema initialized."""
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE,
                    original_path TEXT,
                    current_path TEXT,
                    filename TEXT,
                    category TEXT,
                    document_date TEXT,
                    title TEXT,
                    issuer_or_person TEXT,
                    summary TEXT,
                    readable_text TEXT,
                    app TEXT,
                    tags TEXT,
                    todos_json TEXT,
                    amounts_json TEXT,
                    processed_at TEXT
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title, summary, readable_text, tags, app, issuer_or_person,
                    content='documents', content_rowid='id'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS moves_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT,
                    source_path TEXT,
                    target_path TEXT,
                    moved_at TEXT,
                    undone INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stats_counters (
                    id INTEGER PRIMARY KEY,
                    searches_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("INSERT OR IGNORE INTO stats_counters (id, searches_count) VALUES (1, 0)")
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to connect or initialize SQLite database: {e}")


def log_move(conn, file_hash, source_path, target_path):
    """Log file move operation to support safe, atomic undo."""
    try:
        with conn:
            conn.execute(
                "INSERT INTO moves_log (file_hash, source_path, target_path, moved_at, undone) VALUES (?, ?, ?, ?, 0)",
                (file_hash, str(source_path), str(target_path), datetime.datetime.now().isoformat())
            )
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to log move transaction: {e}")


def index_document(conn, doc_data):
    """Upsert document record and update SQLite FTS5 index."""
    try:
        with conn:
            cur = conn.execute("""
                INSERT OR REPLACE INTO documents (
                    file_hash, original_path, current_path, filename, category,
                    document_date, title, issuer_or_person, summary, readable_text,
                    app, tags, todos_json, amounts_json, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_data["file_hash"],
                doc_data["original_path"],
                doc_data["current_path"],
                doc_data["filename"],
                doc_data["category"],
                doc_data["document_date"],
                doc_data["title"],
                doc_data["issuer_or_person"],
                doc_data["summary"],
                doc_data["readable_text"],
                doc_data["app"],
                doc_data["tags"],
                json.dumps(doc_data.get("todos", [])),
                json.dumps(doc_data.get("amounts", [])),
                datetime.datetime.now().isoformat()
            ))
            doc_id = cur.lastrowid
            conn.execute("""
                INSERT OR REPLACE INTO documents_fts (rowid, title, summary, readable_text, tags, app, issuer_or_person)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                doc_data["title"],
                doc_data["summary"],
                doc_data["readable_text"],
                doc_data["tags"],
                doc_data["app"],
                doc_data["issuer_or_person"]
            ))
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to index document {doc_data.get('filename')}: {e}")
