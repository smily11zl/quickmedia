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
    db.create_tag("宠物")
    db.create_tag("截图")
    db.close()
    yield client
    db = Database(db_path)
    db.execute("DELETE FROM assets")
    db.execute("DELETE FROM tags")
    db.execute("DELETE FROM asset_tags")
    db.execute("DELETE FROM ai_queue")
    db.close()


class TestAssetAPI:
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
    def test_search(self, seeded):
        r = seeded.get("/api/search?q=橘猫")
        assert r.status_code == 200
        data = r.json()
        items = data["items"] if isinstance(data, dict) else data
        assert len(items) == 1
        assert items[0]["filename"] == "cat.png"
        assert "counts" in data


class TestTagAPI:
    def test_list_tags(self, seeded):
        r = seeded.get("/api/tags")
        assert r.status_code == 200
        data = r.json()
        names = {t["name"] for t in data}
        assert "宠物" in names

    def test_add_tag_to_asset(self, seeded):
        tag_id = None
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
        seeded.post(f"/api/assets/1/tags/{tag_id}")
        r = seeded.delete(f"/api/assets/1/tags/{tag_id}")
        assert r.status_code == 200


class TestStatsAPI:
    def test_stats(self, seeded):
        r = seeded.get("/api/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert data["image"] == 1
        assert data["video"] == 1
        assert data["document"] == 1


class TestRetryAI:
    def test_retry_resets_failed_to_pending(self, seeded):
        db = Database(seeded.app.extra["db_path"])
        db.execute(
            "INSERT INTO ai_queue (asset_id, task_type, status, attempt, error) "
            "VALUES (1, 'vision', 'failed', 3, 'timeout')"
        )
        db.close()
        r = seeded.post("/api/assets/1/retry-ai")
        assert r.status_code == 200
        assert r.json()["ok"] is True
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


class TestTranscriptAPI:
    def test_asset_detail_includes_transcript(self, seeded):
        db = Database(seeded.app.extra["db_path"])
        db.conn.execute("UPDATE assets SET transcript='测试转录文本' WHERE id=1")
        db.conn.commit()
        db.close()
        r = seeded.get("/api/assets/1")
        assert r.status_code == 200
        data = r.json()
        assert "transcript" in data
        assert data["transcript"] == "测试转录文本"

    def test_transcript_is_nullable(self, seeded):
        r = seeded.get("/api/assets/2")
        assert r.status_code == 200
        data = r.json()
        assert "transcript" in data
        assert data["transcript"] is None


class TestReanalyzeAPI:
    """Re-analyze endpoints for single and batch re-analysis."""

    def test_reanalyze_re_enqueues_tasks(self, seeded):
        """POST /api/assets/{id}/reanalyze clears results and re-enqueues."""
        db = Database(seeded.app.extra["db_path"])
        db.conn.execute("UPDATE assets SET ai_description='old desc' WHERE id=1")
        db.execute(
            "INSERT INTO ai_queue (asset_id, task_type, status) VALUES (1, 'vision', 'done')"
        )
        db.close()

        r = seeded.post("/api/assets/1/reanalyze")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        db = Database(seeded.app.extra["db_path"])
        rows = db.execute("SELECT ai_description FROM assets WHERE id=1")
        assert rows[0]["ai_description"] is None

        queue_rows = db.execute(
            "SELECT task_type, status FROM ai_queue WHERE asset_id=1 AND status='pending'"
        )
        assert len(queue_rows) >= 1
        db.close()

    def test_batch_reanalyze(self, seeded):
        """POST /api/assets/batch-reanalyze handles multiple assets."""
        r = seeded.post("/api/assets/batch-reanalyze",
                        json={"asset_ids": [1, 2]})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_reanalyze_nonexistent_asset(self, seeded):
        """Reanalyze nonexistent asset returns 404."""
        r = seeded.post("/api/assets/999/reanalyze")
        assert r.status_code == 404


class TestAssetFilters:
    """v4 filter parameters on GET /api/assets."""

    def test_filter_by_format(self, seeded):
        """?formats=png returns only .png assets."""
        r = seeded.get("/api/assets?formats=png")
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            assert item["extension"] == ".png"

    def test_filter_by_single_format(self, seeded):
        """?formats=md returns only .md assets."""
        r = seeded.get("/api/assets?formats=md")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "notes.md"

    def test_filter_by_ai_status(self, seeded):
        """ai_status=failed returns assets with failed AI status."""
        db = Database(seeded.app.extra["db_path"])
        db.execute(
            "INSERT INTO ai_queue (asset_id, task_type, status) VALUES (1, 'vision', 'failed')"
        )
        db.close()
        r = seeded.get("/api/assets?ai_status=failed")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    def test_filter_by_tags(self, seeded):
        """tags=ID returns assets with that tag (union)."""
        db = Database(seeded.app.extra["db_path"])
        # Tag asset 1 with tag "宠物" (id=1)
        db.execute("INSERT INTO asset_tags (asset_id, tag_id, source) VALUES (1, 1, 'manual')")
        db.close()
        r = seeded.get("/api/assets?tags=1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "cat.png"


class TestPromptsAPI:
    """v5 prompts configuration endpoints."""

    def test_get_prompts_returns_all_types(self, client):
        """GET /api/prompts returns all analysis types."""
        r = client.get("/api/prompts")
        assert r.status_code == 200
        data = r.json()
        for key in ("vision", "text", "speech", "video_summary"):
            assert key in data
            assert "presets" in data[key]
            assert "custom" in data[key]

    def test_update_prompts_custom(self, client):
        """PUT /api/prompts updates custom prompt."""
        r = client.put("/api/prompts", json={
            "type": "vision",
            "custom": "请分析图片的构图和色彩"
        })
        assert r.status_code == 200
        # Verify the update persisted
        r2 = client.get("/api/prompts")
        assert r2.json()["vision"]["custom"] == "请分析图片的构图和色彩"

    def test_update_invalid_type_returns_400(self, client):
        """PUT with invalid type returns 400."""
        r = client.put("/api/prompts", json={
            "type": "invalid",
            "custom": "test"
        })
        assert r.status_code == 400
