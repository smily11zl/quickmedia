"""Tests for QuickMedia FastAPI server."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from quickmedia.api.server import create_app
from quickmedia.database import Database
from quickmedia.config import Config


@pytest.fixture
def client():
    """Create a test app with temp database."""
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    thumb_dir = os.path.join(config_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    app = create_app(db, cfg, thumb_dir)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded(client, request):
    """Client with test assets inserted."""
    db_path = client.app.extra["db_path"]
    db = Database(db_path)
    db.execute("""
        INSERT INTO assets (hash, inode, device, path, filename, extension,
                            asset_type, size, width, height, description)
        VALUES
        ('h1', 1, 1, '/tmp/cat.png', 'cat.png', '.png', 'image', 100,
         800, 600, '一只橘猫'),
        ('h2', 2, 2, '/tmp/video.mp4', 'video.mp4', '.mp4', 'video', 2000,
         1920, 1080, NULL),
        ('h3', 3, 3, '/tmp/notes.md', 'notes.md', '.md', 'document', 50,
         NULL, NULL, '项目笔记')
    """)
    # Add tags
    db.create_tag("宠物")
    db.create_tag("截图")
    db.close()
    yield client
    db = Database(db_path)
    db.execute("DELETE FROM assets")
    db.execute("DELETE FROM tags")
    db.execute("DELETE FROM asset_tags")
    db.close()


class TestAssetAPI:
    """Asset listing and detail endpoints."""

    def test_list_assets(self, seeded):
        r = seeded.get("/api/assets")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3

    def test_list_assets_pagination(self, seeded):
        r = seeded.get("/api/assets?offset=0&limit=2")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    def test_list_assets_filter_by_type(self, seeded):
        r = seeded.get("/api/assets?type=image")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["asset_type"] == "image"

    def test_get_asset_detail(self, seeded):
        r = seeded.get("/api/assets/1")
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "cat.png"
        assert data["width"] == 800
        assert data["height"] == 600

    def test_get_nonexistent_asset(self, seeded):
        r = seeded.get("/api/assets/999")
        assert r.status_code == 404

    def test_update_asset_description(self, seeded):
        r = seeded.put("/api/assets/1", json={"description": "可爱的猫"})
        assert r.status_code == 200
        r2 = seeded.get("/api/assets/1")
        assert r2.json()["description"] == "可爱的猫"


class TestSearchAPI:
    """Search endpoint."""

    def test_search(self, seeded):
        r = seeded.get("/api/search?q=橘猫")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["filename"] == "cat.png"


class TestTagAPI:
    """Tag listing and management."""

    def test_list_tags(self, seeded):
        r = seeded.get("/api/tags")
        assert r.status_code == 200
        data = r.json()
        names = {t["name"] for t in data}
        assert "宠物" in names

    def test_add_tag_to_asset(self, seeded):
        tag_id = None
        # Get tag id
        r0 = seeded.get("/api/tags")
        for t in r0.json():
            if t["name"] == "截图":
                tag_id = t["id"]
                break
        r = seeded.post(f"/api/assets/1/tags/{tag_id}")
        assert r.status_code == 200

    def test_remove_tag_from_asset(self, seeded):
        tag_id = None
        r0 = seeded.get("/api/tags")
        for t in r0.json():
            if t["name"] == "宠物":
                tag_id = t["id"]
                break
        # First add
        seeded.post(f"/api/assets/1/tags/{tag_id}")
        # Then remove
        r = seeded.delete(f"/api/assets/1/tags/{tag_id}")
        assert r.status_code == 200


class TestStatsAPI:
    """Stats endpoint."""

    def test_stats(self, seeded):
        r = seeded.get("/api/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert data["image"] == 1
        assert data["video"] == 1
        assert data["document"] == 1


class TestRetryAI:
    """Retry failed AI tasks."""

    def test_retry_resets_failed_to_pending(self, seeded):
        db = Database(seeded.app.extra["db_path"])
        # Insert a failed ai_queue entry for asset 1 (exists in seeded)
        db.execute(
            "INSERT INTO ai_queue (asset_id, task_type, status, attempt, error) "
            "VALUES (1, 'vision', 'failed', 3, 'timeout')"
        )
        db.close()
        r = seeded.post("/api/assets/1/retry-ai")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify status changed
        db = Database(seeded.app.extra["db_path"])
        rows = db.execute(
            "SELECT status, attempt, error FROM ai_queue WHERE asset_id=1"
        )
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["attempt"] == 0
        assert rows[0]["error"] is None
        db.close()

    def test_retry_no_failed_tasks_returns_404(self, seeded):
        r = seeded.post("/api/assets/1/retry-ai")
        assert r.status_code == 404
