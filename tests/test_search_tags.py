"""Tests for search (FTS5) and tag operations."""

import os
import tempfile
from quickmedia.database import Database


def _tmp_db():
    return Database(os.path.join(tempfile.mkdtemp(), "test.db"))


class TestFTSSearch:
    """FTS5 full-text search."""

    def _seed(self, db):
        """Insert test assets for search."""
        db.execute("""
            INSERT INTO assets (hash, path, filename, extension, asset_type,
                                size, description, ai_description, notes)
            VALUES
            ('h1','/tmp/cat.png','cat.png','.png','image',100,
             '一只橘猫',NULL,NULL),
            ('h2','/tmp/dog.jpg','dog.jpg','.jpg','image',200,
             NULL,'一只金毛犬在公园',NULL),
            ('h3','/tmp/readme.md','readme.md','.md','document',50,
             NULL,NULL,'QuickMedia项目笔记')
        """)
        # Rebuild FTS index
        db.execute("INSERT INTO assets_fts(assets_fts) VALUES('rebuild')")

    def test_search_by_filename(self):
        db = _tmp_db()
        self._seed(db)
        results = db.search("cat")
        assert len(results) == 1
        assert results[0]["filename"] == "cat.png"

    def test_search_by_description(self):
        db = _tmp_db()
        self._seed(db)
        results = db.search("橘猫")
        assert len(results) == 1
        assert results[0]["description"] == "一只橘猫"

    def test_search_by_ai_description(self):
        db = _tmp_db()
        self._seed(db)
        results = db.search("金毛")
        assert len(results) == 1
        assert results[0]["filename"] == "dog.jpg"

    def test_search_by_notes(self):
        db = _tmp_db()
        self._seed(db)
        results = db.search("QuickMedia")
        assert len(results) == 1

    def test_search_no_match(self):
        db = _tmp_db()
        self._seed(db)
        results = db.search("不存在的关键词")
        assert len(results) == 0

    def test_search_partial_match(self):
        db = _tmp_db()
        self._seed(db)
        # FTS5 prefix matching
        results = db.search("cat")
        assert len(results) >= 1


class TestTagCRUD:
    """Tag create, read, delete, and asset-tag linking."""

    def test_create_tag(self):
        db = _tmp_db()
        tag_id = db.create_tag("宠物")
        assert tag_id > 0

    def test_create_duplicate_tag_returns_existing(self):
        db = _tmp_db()
        id1 = db.create_tag("宠物")
        id2 = db.create_tag("宠物")
        assert id1 == id2

    def test_list_tags(self):
        db = _tmp_db()
        db.create_tag("宠物")
        db.create_tag("设计")
        tags = db.list_tags()
        names = {t["name"] for t in tags}
        assert "宠物" in names
        assert "设计" in names

    def test_tag_asset(self):
        db = _tmp_db()
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size)"
            " VALUES ('h1','/tmp/a.jpg','a.jpg','.jpg','image',100)"
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        tag_id = db.create_tag("截图")

        db.tag_asset(asset_id, tag_id)

        tags = db.get_asset_tags(asset_id)
        assert len(tags) == 1
        assert tags[0]["name"] == "截图"

    def test_get_asset_tags_empty(self):
        db = _tmp_db()
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size)"
            " VALUES ('h1','/tmp/a.jpg','a.jpg','.jpg','image',100)"
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        tags = db.get_asset_tags(asset_id)
        assert len(tags) == 0

    def test_remove_tag(self):
        db = _tmp_db()
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size)"
            " VALUES ('h1','/tmp/a.jpg','a.jpg','.jpg','image',100)"
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        tag_id = db.create_tag("临时")

        db.tag_asset(asset_id, tag_id)
        db.remove_tag(asset_id, tag_id)

        tags = db.get_asset_tags(asset_id)
        assert len(tags) == 0

    def test_list_tags_with_counts(self):
        db = _tmp_db()
        t1 = db.create_tag("A")
        t2 = db.create_tag("B")
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size)"
            " VALUES ('h1','/tmp/a.jpg','a.jpg','.jpg','image',100)"
        )
        aid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.tag_asset(aid, t1)

        tags = db.list_tags()
        # Find tag A and verify count
        tag_a = next(t for t in tags if t["name"] == "A")
        assert tag_a["count"] == 1
        tag_b = next(t for t in tags if t["name"] == "B")
        assert tag_b["count"] == 0
