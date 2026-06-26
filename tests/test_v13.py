"""Tests for QuickMedia V13 — Graph View API + WebSocket."""
import pytest


class TestV13GraphAPI:
    """Slice 13.1: GET /api/graph endpoint."""

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
        """Seed a test asset and node with association."""
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

    def test_graph_returns_three_sections(self, client, seeded):
        """GET /api/graph returns {nodes, edges, unassigned} sections."""
        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert "unassigned" in data
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "宠物"
        assert data["nodes"][0]["asset_count"] == 1
        assert len(data["edges"]) == 1
        assert data["edges"][0]["node_id"] == seeded["node_id"]
        assert data["edges"][0]["asset_id"] == seeded["asset_id"]
        assert data["unassigned"] == []

    def test_asset_in_multiple_nodes(self, client):
        """Same asset linked to two nodes → two edges."""
        from quickmedia.database import Database
        db_path = client.app.extra["db_path"]
        db = Database(db_path)
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
            "VALUES (?,?,?,?,?,?)",
            ("xyz789", "/tmp/dog.jpg", "dog.jpg", ".jpg", "image", 200),
        )
        aid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.execute("INSERT INTO nodes (name) VALUES (?)", ("宠物",))
        nid1 = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.execute("INSERT INTO nodes (name) VALUES (?)", ("动物",))
        nid2 = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.execute("INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)", (nid1, aid))
        db.execute("INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)", (nid2, aid))

        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        edges = data["edges"]
        assert len(edges) == 2
        node_ids = {e["node_id"] for e in edges}
        assert nid1 in node_ids
        assert nid2 in node_ids
        assert all(e["asset_id"] == aid for e in edges)

    def test_unassigned_assets(self, client):
        """Assets not linked to any node appear in unassigned."""
        from quickmedia.database import Database
        db_path = client.app.extra["db_path"]
        db = Database(db_path)
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
            "VALUES (?,?,?,?,?,?)",
            ("orphan1", "/tmp/orphan.pdf", "orphan.pdf", ".pdf", "document", 50),
        )

        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["unassigned"]) >= 1
        orphan = [a for a in data["unassigned"] if a["filename"] == "orphan.pdf"]
        assert len(orphan) == 1
        assert orphan[0]["asset_type"] == "document"

    def test_graph_empty_db(self, client):
        """Empty DB: nodes=[], edges=[], unassigned=[]."""
        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["unassigned"] == []


class TestV13WebSocket:
    """Slice 13.5: WebSocket endpoint + broadcast."""

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

    def test_websocket_connects_and_receives_broadcast(self, client):
        """WS /ws/graph connects and receives graph_changed on broadcast."""
        with client.websocket_connect("/ws/graph") as ws:
            client.post("/api/nodes", json={"name": "测试"})
            data = ws.receive_json()
            assert data == {"event": "graph_changed"}
