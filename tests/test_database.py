"""Tests for quickmedia.database — SQLite schema and operations."""

import tempfile
import os
from quickmedia.database import Database


def _tmp_db():
    """Create a Database with a temp SQLite file."""
    return Database(os.path.join(tempfile.mkdtemp(), "test.db"))


class TestSchema:
    """Database schema creation and integrity."""

    def test_tables_created(self):
        """Core tables exist after init."""
        db = _tmp_db()
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {r["name"] for r in tables}
        assert "assets" in names
        assert "tags" in names
        assert "asset_tags" in names
        assert "thumbnail_queue" in names
        assert "watch_paths" in names
        assert "config" in names

    def test_fts_table_created(self):
        """FTS5 virtual table exists."""
        db = _tmp_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        names = {r["name"] for r in tables}
        assert "assets_fts" in names

    def test_indexes_created(self):
        """Key indexes are created."""
        db = _tmp_db()
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        names = {r["name"] for r in indexes}
        assert "idx_assets_hash" in names
        assert "idx_assets_status" in names
        assert "idx_assets_asset_type" in names
        assert "idx_assets_inode_device" in names

    def test_assets_schema_columns(self):
        """Assets table has required columns."""
        db = _tmp_db()
        columns = db.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in columns}
        assert "hash" in col_names
        assert "path" in col_names
        assert "filename" in col_names
        assert "extension" in col_names
        assert "mime_type" in col_names
        assert "asset_type" in col_names
        assert "size" in col_names
        assert "width" in col_names
        assert "height" in col_names
        assert "duration" in col_names
        assert "status" in col_names
        assert "thumbnail_status" in col_names
        assert "version_of" in col_names

    def test_tags_schema(self):
        """Tags table has unique name constraint."""
        db = _tmp_db()
        db.execute("INSERT INTO tags (name) VALUES ('test')")
        try:
            db.execute("INSERT INTO tags (name) VALUES ('test')")
            assert False, "Should have raised IntegrityError"
        except db.conn.IntegrityError:
            pass  # expected


class TestStats:
    """Count queries on the database."""

    def test_stats_empty(self):
        """Stats return zero for an empty database."""
        db = _tmp_db()
        stats = db.get_stats()
        assert stats["total"] == 0
        assert stats["image"] == 0
        assert stats["video"] == 0
        assert stats["audio"] == 0
        assert stats["document"] == 0

    def test_stats_after_insert(self):
        """Stats reflect inserted assets."""
        db = _tmp_db()
        db.execute("""
            INSERT INTO assets (hash, path, filename, extension, asset_type, size)
            VALUES ('abc', '/tmp/a.jpg', 'a.jpg', '.jpg', 'image', 100),
                   ('def', '/tmp/b.mp4', 'b.mp4', '.mp4', 'video', 200),
                   ('ghi', '/tmp/c.txt', 'c.txt', '.txt', 'document', 50)
        """)
        stats = db.get_stats()
        assert stats["total"] == 3
        assert stats["image"] == 1
        assert stats["video"] == 1
        assert stats["audio"] == 0
        assert stats["document"] == 1
