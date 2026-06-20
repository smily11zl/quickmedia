"""Tests for V8 semantic search and similarity endpoints."""

import os
import tempfile
from quickmedia.api.server import create_app
from quickmedia.database import Database
from quickmedia.config import Config
from fastapi.testclient import TestClient


def _make_app(config_dir: str):
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    return create_app(db, Config(config_dir=config_dir), os.path.join(config_dir, "thumbnails"))


class TestSemanticSearch:
    def test_search_keyword_mode_default(self):
        """Search without mode parameter uses keyword search."""
        d = tempfile.mkdtemp()
        try:
            app = _make_app(d)
            client = TestClient(app)
            resp = client.get("/api/search?q=test")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_search_semantic_mode_accepted(self):
        """Search with mode=semantic parameter returns 200."""
        d = tempfile.mkdtemp()
        try:
            app = _make_app(d)
            client = TestClient(app)
            resp = client.get("/api/search?q=hello&mode=semantic")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_search_combined_mode_accepted(self):
        """Search with mode=combined parameter returns 200."""
        d = tempfile.mkdtemp()
        try:
            app = _make_app(d)
            client = TestClient(app)
            resp = client.get("/api/search?q=test&mode=combined")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_search_invalid_mode_falls_back(self):
        """Invalid mode parameter falls back to keyword search."""
        d = tempfile.mkdtemp()
        try:
            app = _make_app(d)
            client = TestClient(app)
            resp = client.get("/api/search?q=test&mode=invalid")
            assert resp.status_code == 200
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


class TestSimilarEndpoint:
    def test_similar_nonexistent_asset(self):
        """Similar endpoint returns 404 for missing asset."""
        d = tempfile.mkdtemp()
        try:
            app = _make_app(d)
            client = TestClient(app)
            resp = client.get("/api/assets/99999/similar")
            assert resp.status_code == 404
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
