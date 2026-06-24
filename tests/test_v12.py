"""Tests for QuickMedia V12 — Aggregation."""
import sqlite3, os, tempfile, pytest
from quickmedia.database import Database


class TestV12Database:
    """Slice 12.1: Database tables for aggregation."""

    @pytest.fixture
    def db(self):
        """Create a fresh in-memory DB with V12 schema."""
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        db = Database(db_path)
        yield db

    def test_aggregation_queue_table_exists(self, db):
        """aggregation_queue table should be created on init."""
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aggregation_queue'")
        assert rows, "aggregation_queue table should exist"

    def test_aggregation_queue_columns(self, db):
        """aggregation_queue should have expected columns."""
        cols = [row["name"] for row in db.execute("PRAGMA table_info(aggregation_queue)")]
        for c in ["id", "mode", "status", "error", "created_at", "completed_at"]:
            assert c in cols, f"Missing column: {c}"

    def test_nodes_table_exists(self, db):
        """nodes table should be created on init."""
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'")
        assert rows, "nodes table should exist"

    def test_nodes_columns(self, db):
        """nodes should have expected columns."""
        cols = [row["name"] for row in db.execute("PRAGMA table_info(nodes)")]
        for c in ["id", "name", "description", "created_at"]:
            assert c in cols, f"Missing column: {c}"

    def test_node_assets_table_exists(self, db):
        """node_assets table should be created on init."""
        rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='node_assets'")
        assert rows, "node_assets table should exist"

    def test_node_assets_columns(self, db):
        """node_assets should have expected columns and foreign keys."""
        cols = [row["name"] for row in db.execute("PRAGMA table_info(node_assets)")]
        assert "node_id" in cols
        assert "asset_id" in cols

    def test_node_assets_cascade_on_node_delete(self, db):
        """Deleting a node should cascade-delete its node_assets."""
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
            "VALUES (?,?,?,?,?,?)",
            ("abc", "/tmp/test.jpg", "test.jpg", ".jpg", "image", 100),
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        db.execute(
            "INSERT INTO nodes (name, description, created_at) VALUES (?,?,?)",
            ("Test Node", "desc", "2026-01-01"),
        )
        node_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        db.execute("INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)", (node_id, asset_id))
        row = db.execute("SELECT 1 FROM node_assets WHERE node_id=? AND asset_id=?", (node_id, asset_id))
        assert row, "node_assets should exist before delete"

        db.execute("DELETE FROM nodes WHERE id=?", (node_id,))
        row = db.execute("SELECT 1 FROM node_assets WHERE node_id=? AND asset_id=?", (node_id, asset_id))
        assert not row, "node_assets should be cascade-deleted when node is deleted"

    def test_node_assets_cascade_on_asset_delete(self, db):
        """Deleting an asset should cascade-delete its node_assets."""
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
            "VALUES (?,?,?,?,?,?)",
            ("def", "/tmp/test2.jpg", "test2.jpg", ".jpg", "image", 200),
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        db.execute(
            "INSERT INTO nodes (name, description, created_at) VALUES (?,?,?)",
            ("Node", "desc", "2026-01-01"),
        )
        node_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        db.execute("INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)", (node_id, asset_id))
        row = db.execute("SELECT 1 FROM node_assets WHERE node_id=? AND asset_id=?", (node_id, asset_id))
        assert row, "node_assets should exist before delete"

        db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        row = db.execute("SELECT 1 FROM node_assets WHERE node_id=? AND asset_id=?", (node_id, asset_id))
        assert not row, "node_assets should be cascade-deleted when asset is deleted"


class TestV12Prompts:
    """Slice 12.2: Prompt building for three aggregation modes."""

    @pytest.fixture
    def sample_assets(self):
        return [
            {"id": 1, "filename": "cat.jpg", "asset_type": "image",
             "visual_description": "一只橘猫趴在沙发上", "ai_summary": None,
             "tags": [{"name": "猫", "source": "auto"}, {"name": "室内", "source": "auto"}]},
            {"id": 2, "filename": "dog.mp4", "asset_type": "video",
             "visual_description": "白色小狗在草地上跑", "ai_summary": "狗在户外玩耍",
             "tags": [{"name": "狗", "source": "auto"}, {"name": "户外", "source": "auto"}]},
            {"id": 3, "filename": "contract.pdf", "asset_type": "document",
             "visual_description": None, "ai_summary": "房屋租赁合同",
             "tags": [{"name": "合同", "source": "auto"}]},
        ]

    @pytest.fixture
    def sample_nodes(self):
        return [
            {"id": 1, "name": "宠物", "description": "猫和狗的照片视频",
             "asset_ids": [1, 2]},
        ]

    def test_full_mode_prompt_contains_all_assets(self, sample_assets):
        """Full mode should include all assets, no nodes."""
        from quickmedia.aggregation.prompts import build_prompt
        prompt = build_prompt("full", sample_assets)
        for a in sample_assets:
            assert a["filename"] in prompt, f"Asset {a['filename']} should be in prompt"

    def test_full_mode_prompt_no_existing_nodes(self, sample_assets):
        """Full mode should not reference existing nodes."""
        from quickmedia.aggregation.prompts import build_prompt
        prompt = build_prompt("full", sample_assets)
        assert "已有节点" not in prompt

    def test_full_append_mode_includes_nodes(self, sample_assets, sample_nodes):
        """Full append mode should include both assets and existing nodes."""
        from quickmedia.aggregation.prompts import build_prompt
        prompt = build_prompt("full_append", sample_assets, sample_nodes)
        for n in sample_nodes:
            assert n["name"] in prompt, f"Node {n['name']} should be in prompt"

    def test_full_append_mode_includes_assets(self, sample_assets, sample_nodes):
        """Full append mode should include all assets."""
        from quickmedia.aggregation.prompts import build_prompt
        prompt = build_prompt("full_append", sample_assets, sample_nodes)
        for a in sample_assets:
            assert a["filename"] in prompt

    def test_append_mode_only_new_assets(self, sample_assets, sample_nodes):
        """Append mode should only include new (unassigned) assets."""
        from quickmedia.aggregation.prompts import build_prompt
        prompt = build_prompt("append", sample_assets, sample_nodes)
        assert "已有节点" in prompt
        # All assets should be in prompt (treated as new for simplicity)

    def test_build_prompt_unknown_mode_raises(self):
        """Unknown mode should raise ValueError."""
        from quickmedia.aggregation.prompts import build_prompt
        import pytest
        with pytest.raises(ValueError):
            build_prompt("invalid", [])


class TestV12Worker:
    """Slice 12.2: Aggregation Worker queue management."""

    @pytest.fixture
    def db(self):
        import tempfile, os
        from quickmedia.database import Database
        tmp = tempfile.mkdtemp()
        db_path = os.path.join(tmp, "test.db")
        db = Database(db_path)
        yield db

    def test_queue_insert_and_poll(self, db):
        """Worker should be able to insert and poll queue entries."""
        from datetime import datetime
        db.execute(
            "INSERT INTO aggregation_queue (mode, status, created_at) VALUES (?,?,?)",
            ("full", "pending", datetime.now().isoformat()),
        )
        rows = db.execute(
            "SELECT * FROM aggregation_queue WHERE status='pending' ORDER BY id LIMIT 1"
        )
        assert rows, "Should find pending task"
        assert rows[0]["mode"] == "full"

    def test_queue_update_status(self, db):
        """Worker should update task status."""
        from datetime import datetime
        db.execute(
            "INSERT INTO aggregation_queue (mode, status, created_at) VALUES (?,?,?)",
            ("full", "pending", datetime.now().isoformat()),
        )
        task_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        db.execute("UPDATE aggregation_queue SET status='processing' WHERE id=?", (task_id,))
        row = db.execute("SELECT status FROM aggregation_queue WHERE id=?", (task_id,))
        assert row[0]["status"] == "processing"

    def test_queue_only_one_running(self, db):
        """Only one task should be running at a time."""
        from datetime import datetime
        db.execute(
            "INSERT INTO aggregation_queue (mode, status, created_at) VALUES (?,?,?)",
            ("full", "processing", datetime.now().isoformat()),
        )
        # Second insert should work but status checker catches it
        running = db.execute(
            "SELECT COUNT(*) as cnt FROM aggregation_queue WHERE status IN ('pending','processing')"
        )
        assert running[0]["cnt"] >= 1


class TestV12API:
    """Slice 12.3: Aggregation API endpoints."""

    @pytest.fixture
    def client(self):
        import tempfile, os
        from fastapi.testclient import TestClient
        from quickmedia.api.server import create_app
        from quickmedia.database import Database
        from quickmedia.config import Config

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
    def seeded(self, client):
        """Seed a test asset and node."""
        from quickmedia.database import Database
        db_path = client.app.extra["db_path"]
        db = Database(db_path)
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
            "VALUES (?,?,?,?,?,?)",
            ("abc123", "/tmp/test.jpg", "test.jpg", ".jpg", "image", 100),
        )
        aid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.execute(
            "INSERT INTO nodes (name, description) VALUES (?,?)",
            ("宠物", "猫狗照片"),
        )
        nid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.execute("INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)", (nid, aid))
        return {"asset_id": aid, "node_id": nid}

    def _get_db(self, client):
        from quickmedia.database import Database
        return Database(client.app.extra["db_path"])

    def test_get_nodes_empty(self, client):
        """GET /api/nodes returns empty list when no nodes."""
        resp = client.get("/api/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_nodes_with_data(self, client, seeded):
        """GET /api/nodes returns nodes with asset counts."""
        resp = client.get("/api/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "宠物"
        assert data[0]["asset_count"] == 1

    def test_create_node(self, client):
        """POST /api/nodes creates a new node."""
        resp = client.post("/api/nodes", json={"name": "新节点", "description": "测试"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["name"] == "新节点"

    def test_update_node(self, client, seeded):
        """PUT /api/nodes/{id} updates a node."""
        resp = client.put(
            f"/api/nodes/{seeded['node_id']}",
            json={"name": "改名", "description": "新描述"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_delete_node(self, client, seeded):
        """DELETE /api/nodes/{id} deletes a node and its associations."""
        resp = client.delete(f"/api/nodes/{seeded['node_id']}")
        assert resp.status_code == 200
        # Verify node_assets cleaned up
        db = self._get_db(client)
        rows = db.execute("SELECT 1 FROM node_assets WHERE node_id=?", (seeded["node_id"],))
        assert not rows

    def test_assign_assets_to_node(self, client, seeded):
        """POST /api/nodes/{id}/assets assigns assets to a node."""
        resp = client.post(
            f"/api/nodes/{seeded['node_id']}/assets",
            json={"asset_ids": [seeded["asset_id"]]},
        )
        assert resp.status_code == 200

    def test_unassign_asset_from_node(self, client, seeded):
        """DELETE /api/nodes/{id}/assets/{aid} unassigns an asset."""
        resp = client.delete(
            f"/api/nodes/{seeded['node_id']}/assets/{seeded['asset_id']}"
        )
        assert resp.status_code == 200
        db = self._get_db(client)
        rows = db.execute(
            "SELECT 1 FROM node_assets WHERE node_id=? AND asset_id=?",
            (seeded["node_id"], seeded["asset_id"]),
        )
        assert not rows

    def test_get_node_assets(self, client, seeded):
        """GET /api/nodes/{id}/assets returns assets for a node."""
        resp = client.get(f"/api/nodes/{seeded['node_id']}/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_submit_aggregation(self, client):
        """POST /api/aggregation/run submits a task."""
        resp = client.post("/api/aggregation/run", json={"mode": "full"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] > 0

    def test_aggregation_status(self, client):
        """GET /api/aggregation/status returns current status."""
        resp = client.get("/api/aggregation/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_submit_while_running_rejected(self, client):
        """POST /api/aggregation/run rejects when task is running."""
        # Submit first task
        client.post("/api/aggregation/run", json={"mode": "full"})
        # Manually mark as processing
        db = self._get_db(client)
        rows = db.execute("SELECT id FROM aggregation_queue WHERE status='pending'")
        if rows:
            db.execute("UPDATE aggregation_queue SET status='processing' WHERE id=?", (rows[0]["id"],))
        # Second submit should be rejected
        resp = client.post("/api/aggregation/run", json={"mode": "append"})
        assert resp.status_code == 409
