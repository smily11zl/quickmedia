"""Database layer for QuickMedia — SQLite + FTS5."""

import sqlite3
import os

DB_VERSION = 19  # increment when adding new migration


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
    visual_description TEXT,
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
    visual_description,
    ai_summary,
    notes,
    transcript,
    video_summary,
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

CREATE TABLE IF NOT EXISTS asset_search_terms (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    term     TEXT NOT NULL,
    UNIQUE(asset_id, term)
);

CREATE TABLE IF NOT EXISTS aggregation_queue (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mode           TEXT NOT NULL,
    status         TEXT DEFAULT 'pending',
    error          TEXT,
    nodes_created  INTEGER DEFAULT 0,
    assigned       INTEGER DEFAULT 0,
    created_at     TEXT DEFAULT (datetime('now')),
    completed_at   TEXT
);

CREATE TABLE IF NOT EXISTS nodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS node_assets (
    node_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, asset_id)
);
"""


class Database:
    """SQLite database with schema management."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        current_ver = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if current_ver >= DB_VERSION:
            return  # already up to date
        self._init_schema()
        self._migrate_v9()
        self._migrate_v12()
        self._migrate_v16()
        self._migrate_v18()
        try:
            self.conn.execute(f"PRAGMA user_version={DB_VERSION}")
        except sqlite3.OperationalError:
            pass  # another connection already set it

    def _migrate_v9(self) -> None:
        """V9: rename ai_description to visual_description for existing databases."""
        try:
            cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(assets)").fetchall()]
            if "ai_description" in cols and "visual_description" not in cols:
                self.conn.execute("ALTER TABLE assets RENAME COLUMN ai_description TO visual_description")
                # Rebuild FTS5 index to pick up the new column name
                self.conn.execute("INSERT INTO assets_fts(assets_fts) VALUES('rebuild')")
        except Exception:
            pass

    def _migrate_v16(self) -> None:
        """V16: add nodes_created and assigned columns."""
        try:
            cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(aggregation_queue)").fetchall()]
            if "nodes_created" not in cols:
                self.conn.execute("ALTER TABLE aggregation_queue ADD COLUMN nodes_created INTEGER DEFAULT 0")
            if "assigned" not in cols:
                self.conn.execute("ALTER TABLE aggregation_queue ADD COLUMN assigned INTEGER DEFAULT 0")
        except Exception:
            pass


    def _migrate_v18(self) -> None:
        """v18: add ai_status and ai_status_updated_at columns to assets.
        Migrates and backfills old data.
        """
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(assets)").fetchall()]
        if "ai_status" not in cols:
            self.conn.execute("ALTER TABLE assets ADD COLUMN ai_status TEXT")
        if "ai_status_updated_at" not in cols:
            self.conn.execute("ALTER TABLE assets ADD COLUMN ai_status_updated_at TEXT")
        try:
            self.conn.execute(
            "UPDATE assets SET ai_status=CASE "
            "WHEN visual_description IS NOT NULL OR ai_summary IS NOT NULL "
            "OR transcript IS NOT NULL OR video_summary IS NOT NULL "
            "OR ocr_text IS NOT NULL THEN 'done' ELSE 'pending' END, "
            "ai_status_updated_at=COALESCE(analyzed_at, datetime('now')) "
            "WHERE ai_status IS NULL"
        )
        except Exception:
            pass  # DB locked by another connection, will backfill next startup
    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.conn.executescript(SCHEMA_SQL)
        # v2 schema migration
        self._migrate_v2()
        # v3 schema migration
        self._migrate_v3()
        self.conn.commit()

    def _migrate_v2(self) -> None:
        """Apply v2 schema changes."""
        cols = self.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in cols}
        if "ocr_text" not in col_names:
            self.conn.execute("ALTER TABLE assets ADD COLUMN ocr_text TEXT")
        tables = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = {r["name"] for r in tables}
        if "ai_queue" not in table_names:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_queue (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                    task_type TEXT NOT NULL,
                    status    TEXT DEFAULT 'pending',
                    attempt   INTEGER DEFAULT 0,
                    error     TEXT,
                    created   TEXT DEFAULT (datetime('now'))
                )
            """)

    def _migrate_v3(self) -> None:
        """Apply v3 schema changes: transcript, video_summary columns and FTS rebuild."""
        cols = self.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in cols}
        needs_rebuild = False
        if "transcript" not in col_names:
            self.conn.execute("ALTER TABLE assets ADD COLUMN transcript TEXT")
            needs_rebuild = True
        if "video_summary" not in col_names:
            self.conn.execute("ALTER TABLE assets ADD COLUMN video_summary TEXT")
            needs_rebuild = True
        if "analyzed_at" not in col_names:
            self.conn.execute("ALTER TABLE assets ADD COLUMN analyzed_at TEXT")
        if needs_rebuild:
            self.conn.execute("DROP TABLE IF EXISTS assets_fts")
            self.conn.execute("""
                CREATE VIRTUAL TABLE assets_fts USING fts5(
                    filename,
                    description,
                    visual_description,
                    ai_summary,
                    notes,
                    transcript,
                    video_summary,
                    content='assets',
                    content_rowid='id'
                )
            """)
            self.conn.execute(
                "INSERT INTO assets_fts(assets_fts) VALUES('rebuild')"
            )

    def _migrate_v12(self) -> None:
        """Apply v12 schema changes: aggregation tables for existing DBs.
        New DBs get these from SCHEMA_SQL. This handles upgrades."""
        tables = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = {r["name"] for r in tables}
        if "aggregation_queue" not in table_names:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS aggregation_queue (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode         TEXT NOT NULL,
                    status       TEXT DEFAULT 'pending',
                    error        TEXT,
                    created_at   TEXT DEFAULT (datetime('now')),
                    completed_at TEXT
                )
            """)
        if "nodes" not in table_names:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at  TEXT DEFAULT (datetime('now'))
                )
            """)
        if "node_assets" not in table_names:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS node_assets (
                    node_id  INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                    PRIMARY KEY (node_id, asset_id)
                )
            """)

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
        """Full-text search across filename, description, visual_description, notes.
        
        Uses LIKE for broad compatibility (FTS5 with proper CJK tokenizer
        requires additional configuration).
        """
        pattern = f"%{query}%"
        return self._search_like(pattern)

    def search_tokens(self, tokens: list[str]) -> list[sqlite3.Row]:
        """Search using multiple tokens with OR logic. Each token is matched via LIKE."""
        if not tokens:
            return []
        # Build OR'd LIKE clauses for each token across all text columns
        columns = ["a.filename", "a.description", "a.visual_description",
                   "a.ai_summary", "a.ocr_text", "a.transcript", "a.video_summary",
                   "a.notes", "t.name"]
        conditions = []
        params = []
        for token in tokens:
            pat = f"%{token}%"
            for col in columns:
                conditions.append(f"{col} LIKE ?")
                params.append(pat)
        where = " OR ".join(conditions)
        # Rank by token match count (proxy BM25)
        score_parts = []
        for token in tokens:
            pat = f"%{token}%"
            col_parts = []
            for col in columns:
                col_parts.append(f"CASE WHEN {col} LIKE '{pat}' THEN 1 ELSE 0 END")
            score_parts.append(f"({' + '.join(col_parts)})")
        score_expr = " + ".join(score_parts)
        return self.execute(f"""
            SELECT DISTINCT a.*, ({score_expr}) as _match_score FROM assets a
            LEFT JOIN asset_tags at2 ON a.id = at2.asset_id
            LEFT JOIN tags t ON at2.tag_id = t.id
            WHERE a.status = 'active' AND ({where})
            ORDER BY _match_score DESC, a.filename
        """, params)

    def _search_like(self, pattern: str) -> list[sqlite3.Row]:
        return self.execute("""
            SELECT DISTINCT a.* FROM assets a
            LEFT JOIN asset_tags at2 ON a.id = at2.asset_id
            LEFT JOIN tags t ON at2.tag_id = t.id
            WHERE a.status = 'active' AND (
                a.filename LIKE ? OR
                a.description LIKE ? OR
                a.visual_description LIKE ? OR
                a.ai_summary LIKE ? OR
                a.notes LIKE ? OR
                a.ocr_text LIKE ? OR
                a.transcript LIKE ? OR
                a.video_summary LIKE ? OR
                t.name LIKE ?
            )
            ORDER BY a.filename
        """, (pattern,) * 9)

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
        """Unlink a tag from an asset. Clean orphan tag if no other asset uses it."""
        self.execute(
            "DELETE FROM asset_tags WHERE asset_id=? AND tag_id=?",
            (asset_id, tag_id),
        )
        # Remove orphan tag if no asset still references it
        self.execute(
            "DELETE FROM tags WHERE id=? AND id NOT IN (SELECT DISTINCT tag_id FROM asset_tags)",
            (tag_id,),
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
def _cleanup_v4_tags(db: Database) -> int:
    """Remove auto-generated time/format/type tags. Returns count removed."""
    import re
    removed = 0

    # Time tags: "2026", "2026-06" (source='auto' only)
    time_rows = db.execute(
        "SELECT t.id, t.name FROM tags t "
        "INNER JOIN asset_tags at ON t.id = at.tag_id "
        "WHERE at.source='auto' AND ("
        "  t.name GLOB '[0-9][0-9][0-9][0-9]' OR "
        "  t.name GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'"
        ") GROUP BY t.id"
    )
    for row in time_rows:
        db.conn.execute("DELETE FROM asset_tags WHERE tag_id=? AND source='auto'", (row["id"],))
        removed += 1

    # Format tags: "PNG", "MP4" (uppercase letters/numbers, source='auto')
    fmt_rows = db.execute(
        "SELECT t.id, t.name FROM tags t "
        "INNER JOIN asset_tags at ON t.id = at.tag_id "
        "WHERE at.source='auto' AND t.name GLOB '[A-Z][A-Z0-9]*' "
        "GROUP BY t.id"
    )
    for row in fmt_rows:
        db.conn.execute("DELETE FROM asset_tags WHERE tag_id=? AND source='auto'", (row["id"],))
        removed += 1

    # Type tags: "图片", "视频", "音频", "文档" (source='auto')
    type_tags = ("图片", "视频", "音频", "文档")
    placeholders = ",".join("?" * len(type_tags))
    type_rows = db.execute(
        f"SELECT t.id FROM tags t "
        f"INNER JOIN asset_tags at ON t.id = at.tag_id "
        f"WHERE at.source='auto' AND t.name IN ({placeholders}) "
        f"GROUP BY t.id",
        type_tags,
    )
    for row in type_rows:
        db.conn.execute("DELETE FROM asset_tags WHERE tag_id=? AND source='auto'", (row["id"],))
        removed += 1

    # Clean orphaned tags (no asset_tags link)
    db.conn.execute(
        "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM asset_tags)"
    )
    db.conn.commit()
    return removed



