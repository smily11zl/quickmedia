"""Tests for QuickMedia V14 — Node Enhancements + MCP."""
import os, tempfile, pytest
from fastapi.testclient import TestClient
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.api.server import create_app


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
def seeded(client):
    db_path = client.app.extra["db_path"]
    db = Database(db_path)
    # Insert an asset
    db.execute(
        "INSERT INTO assets (hash, path, filename, extension, asset_type, size) "
        "VALUES (?,?,?,?,?,?)",
        ("abc123", "/tmp/test.jpg", "test.jpg", "jpg", "image", 1024),
    )
    asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
    # Insert a node
    db.execute(
        "INSERT INTO nodes (name, description) VALUES (?,?)",
        ("测试节点", "测试描述"),
    )
    node_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
    # Link them
    db.execute(
        "INSERT INTO node_assets (node_id, asset_id) VALUES (?,?)",
        (node_id, asset_id),
    )
    return {"node_id": node_id, "asset_id": asset_id}


class TestNodeCRUD:
    """Slice 3: Node delete fix + CRUD stability."""

    def test_delete_node_returns_ok(self, client, seeded):
        """DELETE /api/nodes/{id} should return 200 and remove the node."""
        resp = client.delete(f"/api/nodes/{seeded['node_id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_node_removes_from_list(self, client, seeded):
        """After delete, node should not appear in GET /api/nodes."""
        client.delete(f"/api/nodes/{seeded['node_id']}")
        resp = client.get("/api/nodes")
        nodes = resp.json()
        ids = [n["id"] for n in nodes]
        assert seeded["node_id"] not in ids

    def test_delete_node_cascades_node_assets(self, client, seeded):
        """Deleting a node should remove its node_assets entries."""
        client.delete(f"/api/nodes/{seeded['node_id']}")
        db_path = client.app.extra["db_path"]
        db = Database(db_path)
        rows = db.execute(
            "SELECT 1 FROM node_assets WHERE node_id=?",
            (seeded["node_id"],),
        )
        assert not rows

    def test_delete_nonexistent_node_returns_404(self, client):
        """DELETE /api/nodes/{id} with invalid id should return 404."""
        resp = client.delete("/api/nodes/99999")
        assert resp.status_code == 404

    def test_delete_node_preserves_asset(self, client, seeded):
        """Deleting a node should not delete the associated asset."""
        client.delete(f"/api/nodes/{seeded['node_id']}")
        db_path = client.app.extra["db_path"]
        db = Database(db_path)
        rows = db.execute(
            "SELECT 1 FROM assets WHERE id=?",
            (seeded["asset_id"],),
        )
        assert rows, "Asset should still exist after node delete"


class TestCreateNode:
    """Slice 4: Manual node creation."""

    def test_create_node_returns_id(self, client):
        """POST /api/nodes should return the new node id."""
        resp = client.post("/api/nodes", json={"name": "新建", "description": "描述"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["name"] == "新建"

    def test_create_node_empty_name_returns_400(self, client):
        """POST /api/nodes with empty name should return 400."""
        resp = client.post("/api/nodes", json={"name": "", "description": ""})
        assert resp.status_code == 400


class TestAnalyzeAppend:
    """Slice 5: Node analyze-append endpoint."""

    def test_analyze_append_no_candidates(self, client, seeded):
        """When all assets are already connected, return added=0."""
        resp = client.post(f"/api/nodes/{seeded['node_id']}/analyze-append")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["added"] == 0

    def test_analyze_append_nonexistent_node(self, client):
        """Should return 404 for nonexistent node."""
        resp = client.post("/api/nodes/99999/analyze-append")
        assert resp.status_code == 404

    def test_analyze_append_prompt_is_built(self, client, seeded):
        """Prompt function should receive node info and candidates."""
        from quickmedia.aggregation.prompts import build_append_prompt
        # Node with one asset, one candidate unconnected
        candidates = [{"id": 200, "filename": "candidate.jpg", "asset_type": "image", "ai_summary": "A photo"}]
        node_info = {"name": "测试", "description": "测试节点"}
        existing = [{"filename": "test.jpg", "ai_summary": "Test summary"}]
        prompt = build_append_prompt(node_info, existing, candidates)
        assert "测试" in prompt
        assert "candidate.jpg" in prompt
        assert "test.jpg" in prompt


class TestMCPNodeTools:
    """Slice 7: MCP node management tools."""

    @pytest.fixture(autouse=True)
    def _setup_env(self, client):
        """Point MCP tools to the test's config_dir."""
        import os
        os.environ["QUICKMEDIA_HOME"] = client.app.extra["config_dir"]

    def test_list_nodes_returns_list(self, client, seeded):
        """list_nodes should return a list of nodes."""
        from quickmedia.mcp_server import list_nodes
        result = list_nodes()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_get_node_returns_detail(self, client, seeded):
        """get_node should return node detail."""
        from quickmedia.mcp_server import get_node
        result = get_node(node_id=seeded["node_id"])
        assert result.id == seeded["node_id"]

    def test_create_node_via_mcp(self, client):
        """create_node MCP tool."""
        from quickmedia.mcp_server import create_node
        result = create_node(name="MCP节点", description="测试")
        assert result.ok is True
        assert result.asset_id > 0

    def test_update_node_via_mcp(self, client, seeded):
        """update_node MCP tool."""
        from quickmedia.mcp_server import update_node
        result = update_node(node_id=seeded["node_id"], name="改名", description="新")
        assert result.ok is True

    def test_delete_node_via_mcp(self, client, seeded):
        """delete_node MCP tool."""
        from quickmedia.mcp_server import delete_node
        result = delete_node(node_id=seeded["node_id"])
        assert result.ok is True

    def test_remove_assets_from_node(self, client, seeded):
        """remove_assets_from_node MCP tool."""
        from quickmedia.mcp_server import add_assets_to_node, remove_assets_from_node
        add_assets_to_node(node_id=seeded["node_id"], asset_ids=[seeded["asset_id"]])
        result = remove_assets_from_node(node_id=seeded["node_id"], asset_ids=[seeded["asset_id"]])
        assert result.ok is True

    def test_run_aggregation_mcp(self, client, seeded):
        """run_aggregation MCP tool (blocking mode)."""
        from quickmedia.mcp_server import run_aggregation
        result = run_aggregation(mode="append")
        assert result.ok is True

    def test_run_aggregation_invalid_mode(self, client):
        """run_aggregation rejects invalid modes."""
        from quickmedia.mcp_server import run_aggregation
        result = run_aggregation(mode="invalid")
        assert result.ok is False

    def test_get_stats(self, client):
        """get_stats returns stats."""
        from quickmedia.mcp_server import get_stats
        result = get_stats()
        assert result.ok is True
        assert "素材总数" in result.message

    def test_trigger_scan_no_config(self, client):
        """trigger_scan fails without watch paths."""
        from quickmedia.mcp_server import trigger_scan
        result = trigger_scan()
        assert result.ok is False  # No watch paths in test

    def test_add_and_remove_tag(self, client, seeded):
        """add_asset_tag and remove_asset_tag."""
        from quickmedia.mcp_server import add_asset_tag, remove_asset_tag
        r1 = add_asset_tag(asset_id=seeded["asset_id"], tag_name="mcp_test")
        assert r1.ok is True
        r2 = remove_asset_tag(asset_id=seeded["asset_id"], tag_name="mcp_test")
        assert r2.ok is True

    def test_reanalyze_asset(self, client, seeded):
        """reanalyze_asset enqueues AI tasks."""
        from quickmedia.mcp_server import reanalyze_asset
        result = reanalyze_asset(asset_id=seeded["asset_id"])
        assert result.ok is True

