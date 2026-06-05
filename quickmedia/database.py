"""Database layer for QuickMedia — SQLite + FTS5."""

import sqlite3
import os


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hash            TEXT NOT NULL,
    inode           INTEGER,
    device          INTEGER,
    path            TEXT NOT NULL,
    filename        TEXT NOT NULL,
    extension       TEXT NOT NULL,
    mime_type       TEXT,
    asset_type      TEXT NOT NULL,
    size            INTEGER NOT NULL,
    width           INTEGER,
    height          INTEGER,
    duration        REAL,
    exif_data       TEXT,
    description     TEXT,
    ai_description  TEXT,
    ai_summary      TEXT,
    notes           TEXT,
    status          TEXT DEFAULT 'active',
    thumbnail_status TEXT DEFAULT 'pending',
    version_of      INTEGER,
    created_at      TEXT,
    modified_at     TEXT,
    scanned_at      TEXT,
    created         TEXT DEFAULT (datetime('now')),
    updated         TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assets_hash ON assets(hash);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_asset_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_inode_device ON assets(inode, device);

CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
    filename,
    description,
    ai_description,
    ai_summary,
    notes,
    content='assets',
    content_rowid='id'
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS asset_tags (
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    source   TEXT DEFAULT 'manual',
    PRIMARY KEY (asset_id, tag_id)
);

CREATE TABLE IF NOT EXISTS thumbnail_queue (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    status   TEXT DEFAULT 'pending',
    attempt  INTEGER DEFAULT 0,
    error    TEXT,
    created  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watch_paths (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    path      TEXT NOT NULL UNIQUE,
    recursive INTEGER DEFAULT 1,
    max_depth INTEGER DEFAULT 3,
    enabled   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    """SQLite database with schema management."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def execute(self, sql: str, params=()) -> list[sqlite3.Row]:
        """Execute a SQL query and return results as Row objects."""
        cursor = self.conn.execute(sql, params)
        if cursor.description is not None:
            return cursor.fetchall()
        self.conn.commit()
        return []

    def get_stats(self) -> dict:
        """Return count of assets by type and total."""
        rows = self.execute("""
            SELECT asset_type, COUNT(*) as count
            FROM assets
            WHERE status = 'active'
            GROUP BY asset_type
        """)
        stats = {
            "total": 0,
            "image": 0,
            "video": 0,
            "audio": 0,
            "document": 0,
            "other": 0,
        }
        for row in rows:
            t = row["asset_type"]
            c = row["count"]
            stats[t] = c
            stats["total"] += c
        return stats

    # ── search ────────────────────────────────────────────────────

    def search(self, query: str) -> list[sqlite3.Row]:
        """Full-text search across filename, description, ai_description, notes.
        
        Uses LIKE for broad compatibility (FTS5 with proper CJK tokenizer
        requires additional configuration).
        """
        pattern = f"%{query}%"
        return self.execute("""
            SELECT DISTINCT a.* FROM assets a
            LEFT JOIN asset_tags at2 ON a.id = at2.asset_id
            LEFT JOIN tags t ON at2.tag_id = t.id
            WHERE a.status = 'active' AND (
                a.filename LIKE ? OR
                a.description LIKE ? OR
                a.ai_description LIKE ? OR
                a.ai_summary LIKE ? OR
                a.notes LIKE ? OR
                t.name LIKE ?
            )
            ORDER BY a.filename
        """, (pattern,) * 6)

    # ── tags ──────────────────────────────────────────────────────

    def create_tag(self, name: str) -> int:
        """Create a tag, returning its id. Returns existing id if duplicate."""
        existing = self.execute("SELECT id FROM tags WHERE name=?", (name,))
        if existing:
            return existing[0]["id"]
        cursor = self.conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        self.conn.commit()
        return cursor.lastrowid

    def list_tags(self) -> list[sqlite3.Row]:
        """List all tags with asset counts."""
        return self.execute("""
            SELECT t.id, t.name,
                   COUNT(at.asset_id) as count
            FROM tags t
            LEFT JOIN asset_tags at ON t.id = at.tag_id
            GROUP BY t.id
            ORDER BY t.name
        """)

    def tag_asset(self, asset_id: int, tag_id: int) -> None:
        """Link a tag to an asset (idempotent)."""
        existing = self.execute(
            "SELECT 1 FROM asset_tags WHERE asset_id=? AND tag_id=?",
            (asset_id, tag_id),
        )
        if not existing:
            self.execute(
                "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?,?)",
                (asset_id, tag_id),
            )

    def remove_tag(self, asset_id: int, tag_id: int) -> None:
        """Unlink a tag from an asset."""
        self.execute(
            "DELETE FROM asset_tags WHERE asset_id=? AND tag_id=?",
            (asset_id, tag_id),
        )

    def get_asset_tags(self, asset_id: int) -> list[sqlite3.Row]:
        """Get all tags for an asset."""
        return self.execute("""
            SELECT t.id, t.name, at.source
            FROM tags t
            JOIN asset_tags at ON t.id = at.tag_id
            WHERE at.asset_id = ?
            ORDER BY t.name
        """, (asset_id,))

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
