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


class TestV3Migration:
    """v3 schema migration — transcript column and FTS coverage."""

    def test_transcript_column_exists(self):
        """v3 migration adds transcript column."""
        db = _tmp_db()
        columns = db.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in columns}
        assert "transcript" in col_names

    def test_transcript_is_searchable(self):
        """FTS search hits transcript content."""
        db = _tmp_db()
        db.execute("""
            INSERT INTO assets (hash, inode, device, path, filename, extension,
                                asset_type, size, status)
            VALUES ('h1', 1, 1, '/tmp/a.mp4', 'meeting.mp4', '.mp4', 'video',
                    1000, 'active')
        """)
        db.conn.execute("UPDATE assets SET transcript='今天我们讨论预算审批' WHERE id=1")
        db.conn.commit()
        results = db.search("预算审批")
        assert len(results) == 1
        assert results[0]["filename"] == "meeting.mp4"

    def test_video_summary_column_exists(self):
        """v3 migration adds video_summary column."""
        db = _tmp_db()
        columns = db.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in columns}
        assert "video_summary" in col_names

    def test_video_summary_is_searchable(self):
        """FTS search hits video_summary content."""
        db = _tmp_db()
        db.execute("""
            INSERT INTO assets (hash, inode, device, path, filename, extension,
                                asset_type, size, status)
            VALUES ('h1', 1, 1, '/tmp/a.mp4', 'demo.mp4', '.mp4', 'video',
                    2000, 'active')
        """)
        db.conn.execute("UPDATE assets SET video_summary='这是一段关于产品发布的会议录像' WHERE id=1")
        db.conn.commit()
        results = db.search("产品发布")
        assert len(results) == 1
        assert results[0]["filename"] == "demo.mp4"

    def test_analyzed_at_column_exists(self):
        """v3 migration adds analyzed_at column."""
        db = _tmp_db()
        columns = db.execute("PRAGMA table_info(assets)")
        col_names = {r["name"] for r in columns}
        assert "analyzed_at" in col_names


class TestV4TagCleanup:
    """v4 tag cleanup removes auto-generated time/format/type tags."""

    def _seed_tags(self, db):
        """Create sample auto tags and link them to an asset."""
        db.execute("INSERT INTO assets (hash,inode,device,path,filename,extension,asset_type,size,status) VALUES ('x1',1,1,'/t/a.mp4','a.mp4','.mp4','video',100,'active')")
        for name in ["2026", "2026-06", "MP4", "视频", "短片(<5min)", "猫"]:
            tag_id = db.create_tag(name)
            db.execute("INSERT OR IGNORE INTO asset_tags (asset_id, tag_id, source) VALUES (1,?, 'auto')", (tag_id,))

    def test_cleanup_removes_time_tags(self):
        """Time tags (year, year-month) with source=auto are removed."""
        db = _tmp_db()
        self._seed_tags(db)
        from quickmedia.database import _cleanup_v4_tags
        removed = _cleanup_v4_tags(db)
        assert removed > 0
        # Verify "2026" and "2026-06" are gone
        tags = db.execute("SELECT name FROM tags ORDER BY name")
        names = {r["name"] for r in tags}
        assert "2026" not in names
        assert "2026-06" not in names

    def test_cleanup_removes_format_and_type_tags(self):
        """Format tags and type tags with source=auto are removed."""
        db = _tmp_db()
        self._seed_tags(db)
        from quickmedia.database import _cleanup_v4_tags
        _cleanup_v4_tags(db)
        tags = db.execute("SELECT name FROM tags ORDER BY name")
        names = {r["name"] for r in tags}
        assert "MP4" not in names
        assert "视频" not in names

    def test_cleanup_preserves_valid_tags(self):
        """Duration tags and user tags are NOT removed."""
        db = _tmp_db()
        self._seed_tags(db)
        from quickmedia.database import _cleanup_v4_tags
        _cleanup_v4_tags(db)
        tags = db.execute("SELECT name FROM tags ORDER BY name")
        names = {r["name"] for r in tags}
        assert "短片(<5min)" in names
        assert "猫" in names
