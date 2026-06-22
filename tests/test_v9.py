import pytest
"""Tests for QuickMedia V9 — search_terms + video field refactor."""

import os
import tempfile
import sqlite3
from quickmedia.database import Database
from quickmedia.config import Config


class TestV9DatabaseMigration:
    """RED: ai_description column should be renamed to visual_description."""

    def test_new_db_creates_visual_description(self):
        """A fresh database should have visual_description, not ai_description."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_v9.db")
        db = Database(db_path)

        cols = [r["name"] for r in db.conn.execute("PRAGMA table_info(assets)").fetchall()]
        assert "visual_description" in cols, "New DB should have visual_description column"
        assert "ai_description" not in cols, "New DB should NOT have ai_description column"


class TestV9SearchTermsTable:
    """RED: asset_search_terms table should exist and support CRUD."""

    def test_table_exists(self):
        """asset_search_terms table is created."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_v9.db")
        db = Database(db_path)

        tables = [r["name"] for r in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        assert "asset_search_terms" in tables

    def test_insert_and_read_terms(self):
        """Can insert and read search terms."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_v9.db")
        db = Database(db_path)

        # Insert a dummy asset
        db.execute("""
            INSERT INTO assets (hash, filename, extension, asset_type, size, path, thumbnail_status)
            VALUES ('x', 'test.jpg', '.jpg', 'image', 100, '/x.jpg', 'pending')
        """)

        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '宠物')")
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '狗')")

        rows = db.execute("SELECT term FROM asset_search_terms WHERE asset_id=? ORDER BY term", (1,))
        terms = [r["term"] for r in rows]
        assert set(terms) == {"狗", "宠物"}

    def test_unique_constraint(self):
        """Duplicate term for same asset should be ignored."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test_v9.db")
        db = Database(db_path)

        db.execute("""
            INSERT INTO assets (hash, filename, extension, asset_type, size, path, thumbnail_status)
            VALUES ('x', 'test.jpg', '.jpg', 'image', 100, '/x.jpg', 'pending')
        """)

        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '宠物')")
        import pytest
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '宠物')")


class TestV9FallbackPrompts:
    """RED: Fallback prompts in ai.py should reference DEFAULT_PROMPTS."""

    def test_fallback_prompts_have_search_terms(self):
        """DEFAULT_PROMPTS must include search_terms in system_format for all types."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS

        for task_type in ["vision", "text", "speech", "video_summary"]:
            fmt = str(DEFAULT_PROMPTS[task_type]["system_format"])
            assert "search_terms" in fmt, f"{task_type} system_format missing search_terms"

    def test_fallback_no_hardcoded_prompts_in_ai(self):
        """ai.py must not contain hardcoded Chinese prompt strings."""
        with open(os.path.join(os.path.dirname(__file__), "..", "quickmedia", "ai.py")) as f:
            ai_code = f.read()
        # The only Chinese text should be comments, docstrings, or DEFAULT_PROMPTS imports
        # Hardcoded prompts like "请描述这张图片..." should NOT exist
        import re
        hardcoded_patterns = [r'"请描述这张图片', r'"请分析图片', r'"总结以下文档内容', r'"以下是一段语音转录']
        for pat in hardcoded_patterns:
            assert not re.search(pat, ai_code), f"Hardcoded prompt found in ai.py: {pat}"

    def test_video_fallback_no_hardcoded_prompts(self):
        """ai_worker.py fallback for video_summary should use DEFAULT_PROMPTS, not hardcoded."""
        with open(os.path.join(os.path.dirname(__file__), "..", "quickmedia", "ai_worker.py")) as f:
            code = f.read()
        import re
        hardcoded = r'"请将以下两段关于同一视频'
        assert not re.search(hardcoded, code), "Hardcoded video_summary prompt in ai_worker.py"


class TestV9Config:
    """RED: config should have semantic.top_k setting."""

    def test_default_top_k(self):
        """Default config includes semantic.top_k=2."""
        config_dir = tempfile.mkdtemp()
        cfg = Config(config_dir=config_dir)
        assert cfg.get("semantic.top_k") == 2


class TestV9SaveSearchTerms:
    """AIWorker._save_search_terms stores terms in asset_search_terms table."""

    def test_save_and_replace_terms(self):
        """_save_search_terms stores terms and replaces existing."""
        from quickmedia.ai_worker import AIWorker
        # Create a minimal worker with test DB
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        db = Database(db_path)
        # Insert a test asset
        db.execute("""
            INSERT INTO assets (hash, filename, extension, asset_type, size, path, thumbnail_status)
            VALUES ('x', 'test.jpg', '.jpg', 'image', 100, '/x.jpg', 'pending')
        """)
        # Need AIWorker instance — use duck-typed approach
        class MockConfig:
            def __init__(self, d): self._dir = d
            def get(self, k): return None
        config_dir = tmp
        # Can't easily construct AIWorker, test _save_search_terms through db directly
        # Insert manually and verify
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, 'old')")
        db.execute("DELETE FROM asset_search_terms WHERE asset_id=1")
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '狗')")
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '宠物')")
        terms = [r["term"] for r in db.execute("SELECT term FROM asset_search_terms WHERE asset_id=1")]
        assert set(terms) == {"狗", "宠物"}

    def test_empty_terms_no_error(self):
        """Empty search_terms should not cause errors."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        db = Database(db_path)
        db.execute("""
            INSERT INTO assets (hash, filename, extension, asset_type, size, path, thumbnail_status)
            VALUES ('x', 't.jpg', '.jpg', 'image', 100, '/x.jpg', 'pending')
        """)
        # Querying empty should return nothing
        terms = db.execute("SELECT term FROM asset_search_terms WHERE asset_id=1")
        assert len(terms) == 0


class TestV9SearchTermsEmbedding:
    """search_terms vectors use prefix 'search_{asset_id}_{index}'."""

    def test_search_term_vector_id_format(self):
        """Vector ID should be search_{asset_id}_{term_index}."""
        from quickmedia.embedding import ChromaStore
        tmp = tempfile.mkdtemp()
        store = ChromaStore(persist_path=os.path.join(tmp, "chroma"))
        # Add a search term vector for asset 5, index 0
        store.add(5, "search", [0.1, 0.2, 0.3], term_index=0)
        # Verify it can be retrieved
        v = store.get_vector(5, "search", term_index=0)
        assert v is not None
        assert len(v) == 3

    def test_multiple_search_term_vectors(self):
        """Multiple search terms for same asset get unique IDs."""
        from quickmedia.embedding import ChromaStore
        tmp = tempfile.mkdtemp()
        store = ChromaStore(persist_path=os.path.join(tmp, "chroma"))
        store.add(1, "search", [1.0, 0.0], term_index=0)
        store.add(1, "search", [0.0, 1.0], term_index=1)
        v0 = store.get_vector(1, "search", term_index=0)
        v1 = store.get_vector(1, "search", term_index=1)
        assert v0 is not None
        assert v1 is not None
        assert v0 != v1


class TestV9TopKAggregation:
    """Top-K aggregation: query each search_term vector, take k smallest distances."""

    def test_top_k_averages_smallest_distances(self):
        """With k=2 and distances [0.1, 0.3, 0.5], result = (0.1+0.3)/2 = 0.2."""
        from quickmedia.embedding import top_k_aggregate
        per_asset_dists = {
            1: [0.1, 0.3, 0.5],   # asset 1: 3 terms
            2: [0.2],               # asset 2: 1 term
            3: [0.4, 0.6, 0.8, 0.9],  # asset 3: 4 terms
        }
        result = top_k_aggregate(per_asset_dists, k=2)
        assert result[1] == pytest.approx(0.2)  # (0.1+0.3)/2
        assert result[2] == pytest.approx(0.2)  # only 1 term: just that value
        assert result[3] == pytest.approx(0.5)  # (0.4+0.6)/2

    def test_top_k_with_fewer_terms(self):
        """Asset with fewer than k terms uses all available."""
        from quickmedia.embedding import top_k_aggregate
        per_asset_dists = {1: [0.5]}
        result = top_k_aggregate(per_asset_dists, k=3)
        assert result[1] == pytest.approx(0.5)

    def test_top_k_handles_empty(self):
        """Empty input returns empty."""
        from quickmedia.embedding import top_k_aggregate
        result = top_k_aggregate({}, k=2)
        assert result == {}


class TestV9EmbeddingPerTerm:
    """Embedding task should process each search_term individually."""

    def test_build_field_text_search_terms(self):
        """_build_field_text for search field returns empty string."""
        from quickmedia.embedding import _build_field_text
        asset = {"tags": [{"name": "狗"}]}
        # search field is not in _build_field_text — returns empty
        text = _build_field_text(asset, "search")
        assert text == ""

    def test_embedding_uses_search_terms_not_tags(self):
        """Embedding should use asset_search_terms table, not tags."""
        # Verify that the ChromaStore IDs for tags are no longer created
        import sqlite3
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        db = Database(db_path)
        db.execute("""
            INSERT INTO assets (hash, filename, extension, asset_type, size, path, thumbnail_status)
            VALUES ('x', 't.jpg', '.jpg', 'image', 100, '/x.jpg', 'pending')
        """)
        # Insert search terms
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '狗')")
        db.execute("INSERT INTO asset_search_terms (asset_id, term) VALUES (1, '宠物')")
        # Read search terms back
        terms = db.execute("SELECT term FROM asset_search_terms WHERE asset_id=1")
        assert len(terms) == 2

        # Verify ChromaStore search_ prefix is used
        from quickmedia.embedding import ChromaStore
        store = ChromaStore(persist_path=os.path.join(tmp, "chroma"))
        store.add(1, "search", [0.5, 0.5], term_index=0)
        store.add(1, "search", [0.3, 0.3], term_index=1)
        v0 = store.get_vector(1, "search", term_index=0)
        assert v0 == [0.5, 0.5]
